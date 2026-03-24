"""
Self-Correction & Code Validation Service.

Uses lightweight models (Claude Haiku, GPT-4o-mini) to validate code
snippets before streaming to frontend. Ensures quality and correctness.
"""

from typing import Optional, Dict, Any, List
import logging
import re

from app.services.llm_factory import LLMFactory, LLMProvider

logger = logging.getLogger(__name__)


class CodeValidator:
    """Validates code snippets using lightweight models."""

    # Common code block markers
    CODE_BLOCK_PATTERNS = [
        r"```(?P<lang>\w+)?\n(?P<code>.*?)```",  # Markdown code blocks
        r"<code>(?P<code>.*?)</code>",  # HTML code tags
    ]

    SUPPORTED_LANGUAGES = {
        "python": "python",
        "py": "python",
        "javascript": "javascript",
        "js": "javascript",
        "typescript": "typescript",
        "ts": "typescript",
        "java": "java",
        "cpp": "cpp",
        "c++": "cpp",
        "c": "c",
        "sql": "sql",
        "bash": "bash",
        "sh": "bash",
        "yaml": "yaml",
        "yml": "yaml",
        "json": "json",
        "xml": "xml",
        "html": "html",
        "css": "css",
    }

    def __init__(self):
        """Initialize validator with lightweight LLM provider."""
        self.llm_provider = LLMFactory.get_provider(LLMProvider.CLAUDE_HAIKU)

    async def validate_response(
        self,
        response_text: str,
        language: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Validate a text response for code blocks and correctness.

        Args:
            response_text: The LLM response to validate
            language: Optional language hint for code detection

        Returns:
            {
                "valid": bool,
                "code_blocks": [{"language": str, "code": str, "issues": [...]}],
                "has_errors": bool,
                "suggestions": []
            }
        """
        try:
            result = {
                "valid": True,
                "code_blocks": [],
                "has_errors": False,
                "suggestions": [],
            }

            # Extract code blocks from response
            code_blocks = self._extract_code_blocks(response_text, language)

            if not code_blocks:
                logger.debug("No code blocks detected in response")
                return result

            # Validate each code block
            for code_block in code_blocks:
                validation = await self._validate_code_block(
                    code_block["code"],
                    code_block["language"]
                )

                code_block["issues"] = validation.get("errors", [])
                code_block["warnings"] = validation.get("warnings", [])

                result["code_blocks"].append(code_block)

                if validation.get("errors"):
                    result["has_errors"] = True
                    result["valid"] = False

            logger.info(
                f"Response validation: {len(code_blocks)} code blocks, "
                f"errors={result['has_errors']}"
            )

            return result

        except Exception as e:
            logger.error(f"Code validation error: {e}")
            return {
                "valid": True,  # Fail open
                "code_blocks": [],
                "has_errors": False,
                "suggestions": [f"Validation warning: {str(e)}"],
            }

    async def _validate_code_block(
        self,
        code: str,
        language: str
    ) -> Dict[str, Any]:
        """
        Validate a single code block using lightweight model.

        Uses Claude Haiku for fast validation without significant cost impact.
        """
        if not language or language.lower() not in self.SUPPORTED_LANGUAGES:
            return {"valid": True, "errors": [], "warnings": []}

        try:
            # Build validation prompt
            validation_prompt = f"""
Analyze this {language} code for syntax errors, runtime issues, and logical problems.
Be concise and critical. Focus on actual errors, not style.

Code:
```{language}
{code}
```

Return JSON:
{{
    "valid": true/false,
    "errors": ["error1", "error2"],
    "warnings": ["warning1"]
}}
"""

            # Call lightweight model
            response = await self.llm_provider.validate_syntax(code, language)

            return {
                "valid": response.get("valid", True),
                "errors": response.get("errors", []),
                "warnings": response.get("warnings", []),
            }

        except Exception as e:
            logger.warning(f"Syntax validation failed for {language}: {e}")
            return {"valid": True, "errors": [], "warnings": []}

    def _extract_code_blocks(
        self,
        text: str,
        language_hint: Optional[str] = None
    ) -> List[Dict[str, str]]:
        """Extract code blocks from markdown or HTML formatted text."""
        code_blocks = []

        # Try markdown code blocks first (most common)
        for match in re.finditer(self.CODE_BLOCK_PATTERNS[0], text, re.DOTALL):
            lang = match.group("lang") or language_hint or "text"
            code = match.group("code")

            code_blocks.append({
                "language": self._normalize_language(lang),
                "code": code.strip(),
            })

        # If no markdown blocks, try HTML code tags
        if not code_blocks:
            for match in re.finditer(self.CODE_BLOCK_PATTERNS[1], text, re.DOTALL):
                code = match.group("code")
                code_blocks.append({
                    "language": language_hint or "text",
                    "code": code.strip(),
                })

        return code_blocks

    def _normalize_language(self, lang: str) -> str:
        """Normalize language name to standard form."""
        return self.SUPPORTED_LANGUAGES.get(lang.lower(), lang.lower())


class ResponseCorrectionEngine:
    """Implements feedback loop: validate → correct → re-validate."""

    def __init__(self):
        """Initialize correction engine with both heavy and light LLM models."""
        self.heavy_llm = LLMFactory.get_provider()  # Primary model
        self.light_llm = LLMFactory.get_provider(LLMProvider.CLAUDE_HAIKU)
        self.validator = CodeValidator()
        self.max_correction_iterations = 2

    async def correct_response(
        self,
        response_text: str,
        language: Optional[str] = None,
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Perform self-correction loop:
        1. Validate initial response
        2. If errors, use lightweight model to suggest fixes
        3. Feed corrections back to primary model
        4. Return corrected response

        Returns:
            {
                "original": str,
                "corrected": str,
                "iterations": int,
                "validation": {...},
                "corrections_applied": [...]
            }
        """
        result = {
            "original": response_text,
            "corrected": response_text,
            "iterations": 0,
            "validation": None,
            "corrections_applied": [],
        }

        current_text = response_text

        for iteration in range(self.max_correction_iterations):
            # Step 1: Validate
            validation = await self.validator.validate_response(
                current_text, language
            )
            result["validation"] = validation

            if not validation["has_errors"]:
                logger.info(f"Response valid after {iteration} iteration(s)")
                break

            # Step 2: Suggest corrections
            if validation["code_blocks"]:
                correction_prompt = self._build_correction_prompt(
                    validation, current_text, context
                )

                try:
                    correction_response = await self.light_llm.generate(
                        prompt=correction_prompt,
                        system_prompt="You are a code correction expert. Fix the errors and return the corrected code.",
                    )

                    corrected_code = correction_response.get("content", "")
                    result["corrections_applied"].append(
                        f"Iteration {iteration + 1}: {validation['code_blocks'][0]['language']}"
                    )

                    current_text = corrected_code
                    result["iterations"] += 1

                except Exception as e:
                    logger.warning(f"Correction attempt failed: {e}")
                    break

        result["corrected"] = current_text
        return result

    def _build_correction_prompt(
        self,
        validation: Dict[str, Any],
        response_text: str,
        context: Optional[str] = None
    ) -> str:
        """Build prompt for correction model."""
        errors = []
        for block in validation.get("code_blocks", []):
            if block.get("issues"):
                errors.extend(block["issues"])

        prompt = f"""
The following response has code errors that need fixing:

ERRORS:
{chr(10).join(f"- {err}" for err in errors[:5])}

ORIGINAL RESPONSE:
{response_text}

Please provide a corrected version that fixes all errors.
"""

        if context:
            prompt += f"\n\nCONTEXT:\n{context}"

        return prompt


class SelfCorrectionMiddleware:
    """Wraps LLM responses with automatic validation and correction."""

    def __init__(self, enable_correction: bool = True):
        """
        Initialize middleware.

        Args:
            enable_correction: If True, automatically correct errors.
                             If False, only validate and report.
        """
        self.enable_correction = enable_correction
        self.validator = CodeValidator()
        self.correction_engine = ResponseCorrectionEngine() if enable_correction else None

    async def process_response(
        self,
        response_text: str,
        language: Optional[str] = None,
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process LLM response with validation and optional correction.

        Returns enriched response with validation metadata.
        """
        # Always validate
        validation = await self.validator.validate_response(response_text, language)

        result = {
            "text": response_text,
            "validation": validation,
            "corrected": False,
            "iterations": 0,
        }

        # Optionally correct
        if self.enable_correction and validation["has_errors"]:
            try:
                correction_result = await self.correction_engine.correct_response(
                    response_text, language, context
                )

                result.update({
                    "text": correction_result["corrected"],
                    "corrected": True,
                    "iterations": correction_result["iterations"],
                    "corrections": correction_result["corrections_applied"],
                })

                logger.info(
                    f"Response corrected: {correction_result['iterations']} iteration(s)"
                )

            except Exception as e:
                logger.warning(f"Correction failed, using original: {e}")

        return result
