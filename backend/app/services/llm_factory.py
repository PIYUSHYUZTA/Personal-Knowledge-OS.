"""
Multi-Model LLM Provider Factory.
Supports Gemini 1.5 Pro, GPT-4o, Claude 3.5 Sonnet with fallback logic.
"""

from typing import Optional, List, Dict, Any
from abc import ABC, abstractmethod
import logging
from enum import Enum
import json

from app.config import settings

logger = logging.getLogger(__name__)


class LLMProvider(str, Enum):
    """Available LLM providers."""
    CLAUDE = "claude"        # Anthropic Claude 3.5 Sonnet
    GPT4 = "gpt4"           # OpenAI GPT-4o
    GEMINI = "gemini"       # Google Gemini 1.5 Pro
    CLAUDE_HAIKU = "claude-haiku"  # Lightweight for validation


class ModelConfig:
    """Configuration for an LLM model."""

    def __init__(
        self,
        provider: LLMProvider,
        model_id: str,
        api_key: str,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        supports_tools: bool = True,
    ):
        self.provider = provider
        self.model_id = model_id
        self.api_key = api_key
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.supports_tools = supports_tools
        self.cost_per_1k_input = 0.0  # Requires initialization
        self.cost_per_1k_output = 0.0


# Model pricing (as of March 2026)
MODEL_PRICING = {
    "claude-3-5-sonnet": {"input": 3.00, "output": 15.00},  # Per 1M tokens
    "gpt-4o": {"input": 5.00, "output": 15.00},
    "gemini-1.5-pro": {"input": 1.25, "output": 5.00},
    "claude-3-haiku": {"input": 0.25, "output": 1.25},  # For validation
}


class LLMBase(ABC):
    """Abstract base class for LLM providers."""

    def __init__(self, config: ModelConfig):
        self.config = config
        self.total_tokens_used = 0
        self.total_cost = 0.0

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        tools: Optional[List[Dict]] = None,
        stream: bool = False,
    ) -> Dict[str, Any]:
        """Generate response from model."""
        pass

    @abstractmethod
    async def validate_syntax(self, code: str, language: str) -> Dict[str, Any]:
        """Validate code syntax before streaming."""
        pass

    def calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Calculate cost for token usage and track metrics."""
        pricing = MODEL_PRICING.get(self.config.model_id, {})

        input_cost = (input_tokens / 1_000_000) * pricing.get("input", 0)
        output_cost = (output_tokens / 1_000_000) * pricing.get("output", 0)

        total = input_cost + output_cost
        self.total_cost += total
        self.total_tokens_used += input_tokens + output_tokens

        logger.info(f"Model {self.config.model_id}: +{input_tokens}in +{output_tokens}out = ${total:.4f}")

        # Track metrics
        try:
            from app.services.model_monitor import get_usage_tracker
            tracker = get_usage_tracker()
            tracker.track_api_call(
                model_id=self.config.model_id,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                provider_name=self.config.provider.value,
                success=True,
            )
        except Exception as e:
            logger.warning(f"Failed to track metrics: {e}")

        return total


class ClaudeProvider(LLMBase):
    """Anthropic Claude provider."""

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        tools: Optional[List[Dict]] = None,
        stream: bool = False,
    ) -> Dict[str, Any]:
        """Generate response using Claude API."""
        try:
            import anthropic

            client = anthropic.Anthropic(api_key=self.config.api_key)

            messages = [{"role": "user", "content": prompt}]

            kwargs = {
                "model": self.config.model_id,
                "max_tokens": self.config.max_tokens,
                "temperature": self.config.temperature,
                "messages": messages,
            }

            if system_prompt:
                kwargs["system"] = system_prompt

            if tools and self.config.supports_tools:
                kwargs["tools"] = tools

            if stream:
                return await self._stream_response(client, **kwargs)
            else:
                response = client.messages.create(**kwargs)

                self.calculate_cost(
                    response.usage.input_tokens,
                    response.usage.output_tokens
                )

                return {
                    "content": response.content[0].text,
                    "stop_reason": response.stop_reason,
                    "tool_calls": self._extract_tool_calls(response),
                    "usage": {
                        "input_tokens": response.usage.input_tokens,
                        "output_tokens": response.usage.output_tokens,
                    }
                }

        except Exception as e:
            logger.error(f"Claude API error: {e}")
            raise

    async def _stream_response(self, client, **kwargs) -> Dict[str, Any]:
        """Collect streamed response chunks from Claude into a final payload."""
        tokens = []
        stop_reason = None

        with client.messages.stream(**kwargs) as stream:
            for text in stream.text_stream:
                tokens.append(text)

            final = stream.get_final_message()
            stop_reason = final.stop_reason

        return {
            "content": "".join(tokens),
            "stop_reason": stop_reason,
            "streaming": True,
        }

    async def validate_syntax(self, code: str, language: str) -> Dict[str, Any]:
        """Validate code syntax using Claude Haiku (faster/cheaper)."""
        import anthropic

        client = anthropic.Anthropic(api_key=self.config.api_key)

        validation_prompt = f"""Review this {language} code for syntax errors and logical issues.

Code:
```{language}
{code}
```

Provide a JSON response with:
{{"valid": true/false, "errors": [...], "warnings": [...]}}"""

        try:
            response = client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=500,
                messages=[{"role": "user", "content": validation_prompt}],
            )

            return json.loads(response.content[0].text)

        except Exception as e:
            logger.error(f"Syntax validation error: {e}")
            return {"valid": True, "errors": [], "warnings": []}  # Fail open

    def _extract_tool_calls(self, response) -> List[Dict]:
        """Extract tool calls from Claude response."""
        tool_calls = []

        for block in response.content:
            if block.type == "tool_use":
                tool_calls.append({
                    "name": block.name,
                    "input": block.input,
                    "id": block.id,
                })

        return tool_calls


class GPT4Provider(LLMBase):
    """OpenAI GPT-4o provider."""

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        tools: Optional[List[Dict]] = None,
        stream: bool = False,
    ) -> Dict[str, Any]:
        """Generate response using GPT-4o API."""
        try:
            import openai

            client = openai.AsyncOpenAI(api_key=self.config.api_key)

            messages = []

            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})

            messages.append({"role": "user", "content": prompt})

            kwargs = {
                "model": self.config.model_id,
                "max_tokens": self.config.max_tokens,
                "temperature": self.config.temperature,
                "messages": messages,
            }

            if tools and self.config.supports_tools:
                kwargs["tools"] = [{"type": "function", "function": t} for t in tools]

            if stream:
                return await self._stream_response(client, **kwargs)
            else:
                response = await client.chat.completions.create(**kwargs)

                self.calculate_cost(
                    response.usage.prompt_tokens,
                    response.usage.completion_tokens
                )

                return {
                    "content": response.choices[0].message.content,
                    "stop_reason": response.choices[0].finish_reason,
                    "tool_calls": self._extract_tool_calls(response),
                    "usage": {
                        "input_tokens": response.usage.prompt_tokens,
                        "output_tokens": response.usage.completion_tokens,
                    }
                }

        except Exception as e:
            logger.error(f"GPT-4 API error: {e}")
            raise

    async def _stream_response(self, client, **kwargs) -> Dict[str, Any]:
        """Collect streamed GPT-4 chunks into a final payload."""
        tokens = []

        stream = await client.chat.completions.create(**kwargs, stream=True)

        async for chunk in stream:
            if chunk.choices[0].delta.content:
                tokens.append(chunk.choices[0].delta.content)

        return {
            "content": "".join(tokens),
            "streaming": True,
        }

    async def validate_syntax(self, code: str, language: str) -> Dict[str, Any]:
        """Validate code syntax using GPT-4."""
        import openai

        client = openai.AsyncOpenAI(api_key=self.config.api_key)

        validation_prompt = f"""Review this {language} code for syntax errors.

Code:
```{language}
{code}
```

JSON: {{"valid": true/false, "errors": []}}"""

        try:
            response = await client.chat.completions.create(
                model="gpt-4o-mini",
                max_tokens=300,
                messages=[{"role": "user", "content": validation_prompt}],
            )

            return json.loads(response.choices[0].message.content)

        except Exception as e:
            logger.error(f"Syntax validation error: {e}")
            return {"valid": True, "errors": []}

    def _extract_tool_calls(self, response) -> List[Dict]:
        """Extract tool calls from GPT response."""
        tool_calls = []

        if response.choices[0].message.tool_calls:
            for call in response.choices[0].message.tool_calls:
                tool_calls.append({
                    "name": call.function.name,
                    "input": json.loads(call.function.arguments),
                    "id": call.id,
                })

        return tool_calls


class GeminiProvider(LLMBase):
    """Google Gemini provider."""

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        tools: Optional[List[Dict]] = None,
        stream: bool = False,
    ) -> Dict[str, Any]:
        """Generate response using Gemini API."""
        try:
            import google.generativeai as genai

            genai.configure(api_key=self.config.api_key)
            model = genai.GenerativeModel(
                self.config.model_id,
                system_instruction=system_prompt,
            )

            kwargs = {
                "generation_config": {
                    "max_output_tokens": self.config.max_tokens,
                    "temperature": self.config.temperature,
                }
            }

            if tools and self.config.supports_tools:
                kwargs["tools"] = tools

            if stream:
                return await self._stream_response(model, prompt, **kwargs)
            else:
                response = await model.generate_content_async(prompt, **kwargs)
                # Validate response has candidates
                if not response.candidates or not hasattr(response, 'text'):
                    logger.error(f"Gemini API returned no candidates or invalid response: {response}")
                    return {
                        "content": "I'm sorry, I couldn't generate a response for that. The API returned an empty result.",
                        "stop_reason": "empty_response",
                        "usage": {"input_tokens": 0, "output_tokens": 0}
                    }

                content = response.text
                # Estimate tokens (~4 chars per token)
                input_tokens = len(prompt) // 4
                output_tokens = len(content) // 4

                self.calculate_cost(input_tokens, output_tokens)

                return {
                    "content": content,
                    "stop_reason": response.candidates[0].finish_reason if response.candidates else "unknown",
                    "tool_calls": self._extract_tool_calls(response),
                    "usage": {
                        "input_tokens": input_tokens,
                        "output_tokens": output_tokens,
                    }
                }

        except Exception as e:
            logger.info(f"FATAL LLM ERROR: {e}")
            import traceback
            logger.info(traceback.format_exc())
            raise

    async def _stream_response(self, model, prompt, **kwargs):
        """Collect streamed Gemini chunks into a final payload."""
        tokens = []

        response = model.generate_content(prompt, stream=True, **kwargs)

        for chunk in response:
            if chunk.text:
                tokens.append(chunk.text)

        return {
            "content": "".join(tokens),
            "streaming": True,
        }

    async def validate_syntax(self, code: str, language: str) -> Dict[str, Any]:
        """Validate code using Gemini Flash."""
        import google.generativeai as genai

        genai.configure(api_key=self.config.api_key)

        validation_prompt = f"""Check {language} syntax.
```{language}
{code}
```
JSON: {{"valid": true/false}}"""

        try:
            model = genai.GenerativeModel("gemini-1.5-flash")
            response = model.generate_content(validation_prompt)

            return json.loads(response.text)

        except Exception as e:
            logger.error(f"Syntax validation error: {e}")
            return {"valid": True}

    def _extract_tool_calls(self, response) -> List[Dict]:
        """Extract tool calls from Gemini response."""
        tool_calls = []

        if response.candidates and response.candidates[0].content.parts:
            for part in response.candidates[0].content.parts:
                if hasattr(part, "function_call"):
                    tool_calls.append({
                        "name": part.function_call.name,
                        "input": dict(part.function_call.args),
                    })

        return tool_calls


class LLMFactory:
    """Factory for creating and managing LLM providers with fallback logic."""

    # Provider selection order (primary → fallback)
    PRIMARY_MODELS = [
        LLMProvider.CLAUDE,
    ]

    FALLBACK_MODELS = [
        LLMProvider.GPT4,
        LLMProvider.GEMINI,
    ]

    _providers: Dict[LLMProvider, LLMBase] = {}

    @classmethod
    def initialize(cls):
        """Initialize all configured providers."""

        # Claude (Primary)
        if hasattr(settings, 'CLAUDE_API_KEY') and settings.CLAUDE_API_KEY:
            config = ModelConfig(
                provider=LLMProvider.CLAUDE,
                model_id="claude-3-5-sonnet-20241022",
                api_key=settings.CLAUDE_API_KEY,
                max_tokens=4096,
                temperature=0.7,
                supports_tools=True,
            )
            cls._providers[LLMProvider.CLAUDE] = ClaudeProvider(config)
            logger.info("Claude provider initialized")

        # GPT-4 (Fallback)
        if hasattr(settings, 'OPENAI_API_KEY') and settings.OPENAI_API_KEY:
            config = ModelConfig(
                provider=LLMProvider.GPT4,
                model_id="gpt-4o",
                api_key=settings.OPENAI_API_KEY,
                max_tokens=4096,
                supports_tools=True,
            )
            cls._providers[LLMProvider.GPT4] = GPT4Provider(config)
            logger.info("GPT-4 provider initialized")

        # Gemini (Fallback)
        if hasattr(settings, 'GEMINI_API_KEY') and settings.GEMINI_API_KEY:
            config = ModelConfig(
                provider=LLMProvider.GEMINI,
                model_id="gemini-1.5-flash", # Use Flash for reliability and speed
                api_key=settings.GEMINI_API_KEY,
                supports_tools=True,
            )
            cls._providers[LLMProvider.GEMINI] = GeminiProvider(config)
            logger.info("Gemini 1.5 Pro provider initialized")

    @classmethod
    def get_provider(cls, preferred: Optional[LLMProvider] = None) -> LLMBase:
        """Get LLM provider with fallback logic."""

        if not cls._providers:
            print("DEBUG: No providers initialized, calling initialize()")
            cls.initialize()

        if not cls._providers:
            print("DEBUG: Still no providers after initialization!")
            raise RuntimeError("No LLM providers available")

        # Use preferred if available
        if preferred and preferred in cls._providers:
            return cls._providers[preferred]

        # Use primary model
        for model in cls.PRIMARY_MODELS:
            if model in cls._providers:
                return cls._providers[model]

        # Fall back to alternatives
        for model in cls.FALLBACK_MODELS:
            if model in cls._providers:
                logger.warning(f"Primary model unavailable, using fallback: {model}")
                return cls._providers[model]

        raise RuntimeError("No LLM providers available")

    @classmethod
    def get_stats(cls) -> Dict[str, Any]:
        """Get usage statistics across all providers."""
        stats = {}

        for provider, llm in cls._providers.items():
            stats[provider.value] = {
                "total_tokens": llm.total_tokens_used,
                "total_cost": f"${llm.total_cost:.2f}",
                "model_id": llm.config.model_id,
            }

        return stats
