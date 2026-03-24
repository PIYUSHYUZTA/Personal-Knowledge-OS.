"""
Model Monitoring & Cost Tracking Service.

Tracks API usage, token consumption, costs, and model selection metrics.
Provides insights into LLM provider performance and cost optimization.
"""

from typing import Optional, Dict, Any, List
import logging
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from sqlalchemy.orm import Session
import json

from app.models import AuraState
from app.services.llm_factory import LLMFactory, LLMProvider, MODEL_PRICING

logger = logging.getLogger(__name__)


@dataclass
class ModelMetrics:
    """Metrics for a single LLM provider."""
    provider: str
    model_id: str
    total_requests: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cost: float = 0.0
    avg_tokens_per_request: float = 0.0
    fallback_count: int = 0
    error_count: int = 0
    success_rate: float = 0.0
    last_used: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            **asdict(self),
            "last_used": self.last_used.isoformat() if self.last_used else None,
            "total_cost_formatted": f"${self.total_cost:.4f}",
            "avg_cost_per_request": f"${self.total_cost / max(1, self.total_requests):.4f}" if self.total_requests > 0 else "$0.00",
        }


class ModelUsageTracker:
    """Tracks LLM API usage and costs."""

    def __init__(self, db_session: Optional[Session] = None):
        """Initialize tracker."""
        self.db_session = db_session
        self.metrics: Dict[str, ModelMetrics] = self._initialize_metrics()

    def _initialize_metrics(self) -> Dict[str, ModelMetrics]:
        """Initialize metrics for all available providers."""
        metrics = {}

        for provider, pricing in MODEL_PRICING.items():
            model_name = provider.split("-")[0]  # Extract provider name
            metrics[provider] = ModelMetrics(
                provider=model_name,
                model_id=provider,
            )

        return metrics

    async def track_api_call(
        self,
        model_id: str,
        input_tokens: int,
        output_tokens: int,
        provider_name: str,
        success: bool = True,
        is_fallback: bool = False,
        error_message: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Track an LLM API call.

        Args:
            model_id: Model identifier (e.g., 'claude-3-5-sonnet-20241022')
            input_tokens: Number of input tokens used
            output_tokens: Number of output tokens generated
            provider_name: Provider name (claude, gpt4, gemini)
            success: Whether the call succeeded
            is_fallback: Whether this was a fallback provider
            error_message: Error message if call failed

        Returns:
            Tracking metrics for this call
        """
        try:
            metrics = self.metrics.get(model_id)

            if not metrics:
                logger.warning(f"Unknown model: {model_id}")
                return {}

            # Update metrics
            metrics.total_requests += 1
            metrics.total_input_tokens += input_tokens
            metrics.total_output_tokens += output_tokens

            if is_fallback:
                metrics.fallback_count += 1

            if not success:
                metrics.error_count += 1
            else:
                metrics.avg_tokens_per_request = (
                    (metrics.total_input_tokens + metrics.total_output_tokens) /
                    metrics.total_requests
                )

            metrics.success_rate = (
                (metrics.total_requests - metrics.error_count) /
                metrics.total_requests * 100
            )

            metrics.last_used = datetime.utcnow()

            # Calculate cost
            pricing = MODEL_PRICING.get(model_id, {})
            input_cost = (input_tokens / 1_000_000) * pricing.get("input", 0)
            output_cost = (output_tokens / 1_000_000) * pricing.get("output", 0)
            call_cost = input_cost + output_cost
            metrics.total_cost += call_cost

            logger.info(
                f"Tracked {provider_name}: {input_tokens}in + {output_tokens}out "
                f"= ${call_cost:.6f} (fallback={is_fallback}, success={success})"
            )

            return {
                "model": model_id,
                "provider": provider_name,
                "tokens_used": input_tokens + output_tokens,
                "cost": call_cost,
                "is_fallback": is_fallback,
                "success": success,
            }

        except Exception as e:
            logger.error(f"Error tracking API call: {e}")
            return {}

    def get_provider_metrics(self, model_id: Optional[str] = None) -> Dict[str, Any]:
        """Get metrics for specific model or all models."""
        if model_id:
            metrics = self.metrics.get(model_id)
            return metrics.to_dict() if metrics else {}

        return {
            model_id: metrics.to_dict()
            for model_id, metrics in self.metrics.items()
        }

    def get_summary_metrics(self) -> Dict[str, Any]:
        """Get overall usage summary."""
        total_requests = sum(m.total_requests for m in self.metrics.values())
        total_input = sum(m.total_input_tokens for m in self.metrics.values())
        total_output = sum(m.total_output_tokens for m in self.metrics.values())
        total_cost = sum(m.total_cost for m in self.metrics.values())

        fallback_requests = sum(m.fallback_count for m in self.metrics.values())
        error_requests = sum(m.error_count for m in self.metrics.values())
        success_rate = (
            (total_requests - error_requests) / total_requests * 100
            if total_requests > 0 else 0
        )

        return {
            "total_requests": total_requests,
            "total_tokens": total_input + total_output,
            "total_input_tokens": total_input,
            "total_output_tokens": total_output,
            "total_cost": total_cost,
            "total_cost_formatted": f"${total_cost:.4f}",
            "avg_tokens_per_request": (
                (total_input + total_output) / total_requests
                if total_requests > 0 else 0
            ),
            "avg_cost_per_request": (
                total_cost / total_requests if total_requests > 0 else 0
            ),
            "fallback_count": fallback_requests,
            "error_count": error_requests,
            "success_rate": f"{success_rate:.1f}%",
        }

    def get_cost_by_provider(self) -> Dict[str, float]:
        """Get total cost breakdown by provider."""
        cost_breakdown = {}

        for model_id, metrics in self.metrics.items():
            provider = metrics.provider
            if provider not in cost_breakdown:
                cost_breakdown[provider] = 0.0
            cost_breakdown[provider] += metrics.total_cost

        return {
            k: f"${v:.4f}" for k, v in sorted(
                cost_breakdown.items(),
                key=lambda x: x[1],
                reverse=True
            )
        }

    def reset_metrics(self, model_id: Optional[str] = None):
        """Reset metrics for a specific model or all models."""
        if model_id:
            if model_id in self.metrics:
                self.metrics[model_id] = ModelMetrics(
                    provider=self.metrics[model_id].provider,
                    model_id=model_id,
                )
                logger.info(f"Reset metrics for {model_id}")
        else:
            self.metrics = self._initialize_metrics()
            logger.info("Reset all metrics")


class ModelSelectionOptimizer:
    """Optimizes LLM provider selection based on cost and performance."""

    def __init__(self, tracker: ModelUsageTracker):
        """Initialize optimizer with a usage tracker."""
        self.tracker = tracker
        self.selection_history: List[Dict[str, Any]] = []

    def select_best_provider(
        self,
        preferred: Optional[LLMProvider] = None,
        criteria: str = "cost"  # Options: cost, performance, reliability
    ) -> LLMProvider:
        """
        Select best provider based on criteria.

        Args:
            preferred: Preferred provider if available
            criteria: Optimization criteria (cost, performance, reliability)

        Returns:
            Recommended LLMProvider
        """
        available_providers = {
            "claude": LLMProvider.CLAUDE,
            "gpt4": LLMProvider.GPT4,
            "gemini": LLMProvider.GEMINI,
        }

        if criteria == "cost":
            # Select provider with lowest cost per token
            best_provider = self._select_by_cost()
        elif criteria == "reliability":
            # Select provider with highest success rate
            best_provider = self._select_by_reliability()
        else:  # performance (speed, quality)
            # Select based on success rate + response quality
            best_provider = self._select_by_reliability()

        # Log selection
        self.selection_history.append({
            "timestamp": datetime.utcnow().isoformat(),
            "criteria": criteria,
            "selected_provider": best_provider.value,
            "preferred": preferred.value if preferred else None,
        })

        return best_provider

    def _select_by_cost(self) -> LLMProvider:
        """Select provider with lowest average cost per request."""
        cost_per_request = {}

        for model_id, metrics in self.tracker.metrics.items():
            if metrics.total_requests == 0:
                continue

            avg_cost = metrics.total_cost / metrics.total_requests
            provider_key = metrics.provider

            if provider_key not in cost_per_request:
                cost_per_request[provider_key] = (avg_cost, model_id)
            elif avg_cost < cost_per_request[provider_key][0]:
                cost_per_request[provider_key] = (avg_cost, model_id)

        if not cost_per_request:
            return LLMProvider.CLAUDE

        best = min(cost_per_request.items(), key=lambda x: x[1][0])
        logger.info(f"Cost optimization selected {best[0]}: ${best[1][0]:.6f}/request")

        provider_map = {
            "claude": LLMProvider.CLAUDE,
            "gpt4": LLMProvider.GPT4,
            "gemini": LLMProvider.GEMINI,
        }

        return provider_map.get(best[0], LLMProvider.CLAUDE)

    def _select_by_reliability(self) -> LLMProvider:
        """Select provider with highest success rate."""
        reliability_scores = {}

        for model_id, metrics in self.tracker.metrics.items():
            if metrics.total_requests == 0:
                continue

            provider_key = metrics.provider
            if provider_key not in reliability_scores:
                reliability_scores[provider_key] = (metrics.success_rate, model_id)
            elif metrics.success_rate > reliability_scores[provider_key][0]:
                reliability_scores[provider_key] = (metrics.success_rate, model_id)

        if not reliability_scores:
            return LLMProvider.CLAUDE

        best = max(reliability_scores.items(), key=lambda x: x[1][0])
        logger.info(
            f"Reliability optimization selected {best[0]}: {best[1][0]:.1f}% success rate"
        )

        provider_map = {
            "claude": LLMProvider.CLAUDE,
            "gpt4": LLMProvider.GPT4,
            "gemini": LLMProvider.GEMINI,
        }

        return provider_map.get(best[0], LLMProvider.CLAUDE)

    def get_recommendation_history(self) -> List[Dict[str, Any]]:
        """Get history of provider selections."""
        return self.selection_history


# Global tracker instance
_usage_tracker: Optional[ModelUsageTracker] = None
_selection_optimizer: Optional[ModelSelectionOptimizer] = None


def get_usage_tracker() -> ModelUsageTracker:
    """Get or initialize global usage tracker."""
    global _usage_tracker
    if _usage_tracker is None:
        _usage_tracker = ModelUsageTracker()
    return _usage_tracker


def get_selection_optimizer() -> ModelSelectionOptimizer:
    """Get or initialize global selection optimizer."""
    global _selection_optimizer
    if _selection_optimizer is None:
        tracker = get_usage_tracker()
        _selection_optimizer = ModelSelectionOptimizer(tracker)
    return _selection_optimizer
