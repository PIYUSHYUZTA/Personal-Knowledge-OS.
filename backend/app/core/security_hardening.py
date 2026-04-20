"""
Production Security Hardening Module.

Implements:
- Rate limiting per user/endpoint
- Request validation
- API key management
- HTTPS enforcement
- Error sanitization
- Input validation
"""

from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
import logging
import time
from typing import Optional, Dict, Any, Callable
from functools import wraps
from collections import defaultdict
from datetime import datetime, timedelta
import os

logger = logging.getLogger(__name__)


class RateLimiter:
    """Rate limiting implementation for API endpoints."""

    def __init__(self, requests_per_minute: int = 60, requests_per_hour: int = 1000):
        """
        Initialize rate limiter.

        Args:
            requests_per_minute: Max requests per minute per user
            requests_per_hour: Max requests per hour per user
        """
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self.user_requests: Dict[str, list] = defaultdict(list)

    def is_rate_limited(self, user_id: str) -> tuple[bool, Optional[str]]:
        """
        Check if user is rate limited.

        Returns:
            (is_limited, reason)
        """
        now = time.time()
        one_minute_ago = now - 60
        one_hour_ago = now - 3600

        # Clean old entries
        if user_id in self.user_requests:
            self.user_requests[user_id] = [
                t for t in self.user_requests[user_id]
                if t > one_hour_ago
            ]

        requests = self.user_requests[user_id]

        # Check minute limit
        recent_minute = [t for t in requests if t > one_minute_ago]
        if len(recent_minute) >= self.requests_per_minute:
            return True, f"Rate limit exceeded: {self.requests_per_minute} requests/minute"

        # Check hour limit
        if len(requests) >= self.requests_per_hour:
            return True, f"Rate limit exceeded: {self.requests_per_hour} requests/hour"

        # Record this request
        self.user_requests[user_id].append(now)
        return False, None

    def get_remaining_requests(self, user_id: str) -> Dict[str, int]:
        """Get remaining requests for user."""
        now = time.time()
        one_minute_ago = now - 60
        one_hour_ago = now - 3600

        requests = self.user_requests.get(user_id, [])
        recent_minute = len([t for t in requests if t > one_minute_ago])
        recent_hour = len([t for t in requests if t > one_hour_ago])

        return {
            "minute": max(0, self.requests_per_minute - recent_minute),
            "hour": max(0, self.requests_per_hour - recent_hour),
        }


class APIKeyManager:
    """Secure API key management."""

    def __init__(self):
        """Initialize key manager."""
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.cache_ttl = 300  # 5 minutes

    def validate_api_key(self, api_key: str) -> tuple[bool, Optional[str]]:
        """
        Validate an API key (checks format and environment).

        Args:
            api_key: API key to validate

        Returns:
            (is_valid, error_message)
        """
        if not api_key:
            return False, "API key is required"

        if len(api_key) < 10:
            return False, "API key format is invalid"

        # Check if it matches known provider formats
        valid_prefixes = ["sk-", "AIza", "key_"]  # Common formats
        if not any(api_key.startswith(p) for p in valid_prefixes):
            return False, "API key format is invalid"

        return True, None

    def mask_api_key(self, api_key: str) -> str:
        """Return masked version of API key for logging."""
        if not api_key:
            return "***"
        return f"{api_key[:4]}...{api_key[-4:]}"

    def get_safe_config(self, provider_name: str) -> Dict[str, Any]:
        """
        Get safe configuration for a provider without exposing secrets.

        Args:
            provider_name: Name of provider (claude, gpt4, gemini)

        Returns:
            Safe configuration dictionary
        """
        # This would be fetched from environment in production
        safe_configs = {
            "claude": {
                "model_id": "claude-3-5-sonnet-20241022",
                "provider": "anthropic",
                "supports_tools": True,
                "api_key_set": bool(os.getenv("CLAUDE_API_KEY")),
            },
            "gpt4": {
                "model_id": "gpt-4o",
                "provider": "openai",
                "supports_tools": True,
                "api_key_set": bool(os.getenv("OPENAI_API_KEY")),
            },
            "gemini": {
                "model_id": "gemini-1.5-pro-latest",
                "provider": "google",
                "supports_tools": True,
                "api_key_set": bool(os.getenv("GEMINI_API_KEY")),
            },
        }

        return safe_configs.get(provider_name, {})


class RequestValidator:
    """Validates incoming requests for security and format."""

    @staticmethod
    def validate_query_string(query: str, max_length: int = 2000) -> tuple[bool, Optional[str]]:
        """Validate query string."""
        if not query:
            return False, "Query cannot be empty"

        if len(query) > max_length:
            return False, f"Query exceeds max length of {max_length} characters"

        # Check for injection attempts
        dangerous_patterns = ["<script", "javascript:", "sql", "union select"]
        if any(pattern in query.lower() for pattern in dangerous_patterns):
            return False, "Query contains potentially dangerous patterns"

        return True, None

    @staticmethod
    def validate_json_payload(
        payload: Dict[str, Any],
        required_fields: Optional[list] = None,
        max_size_mb: int = 10
    ) -> tuple[bool, Optional[str]]:
        """Validate JSON payload."""
        if not payload:
            return False, "Payload cannot be empty"

        # Check required fields
        if required_fields:
            missing = [f for f in required_fields if f not in payload]
            if missing:
                return False, f"Missing required fields: {', '.join(missing)}"

        # Check size (rough estimate)
        import json
        payload_size = len(json.dumps(payload)) / (1024 * 1024)
        if payload_size > max_size_mb:
            return False, f"Payload exceeds max size of {max_size_mb}MB"

        return True, None

    @staticmethod
    def sanitize_string(text: str, max_length: int = 1000) -> str:
        """Sanitize string input by removing potentially harmful content."""
        # Remove control characters
        text = "".join(char for char in text if ord(char) >= 32 or char in "\n\r\t")

        # Truncate if too long
        if len(text) > max_length:
            text = text[:max_length]

        return text


class ErrorSanitizer:
    """Sanitizes error messages to avoid leaking internal details."""

    # Map internal error types to safe messages
    ERROR_MESSAGES = {
        "DatabaseError": "Database operation failed",
        "ConnectionError": "Service temporarily unavailable",
        "TimeoutError": "Request timed out",
        "ValidationError": "Invalid input provided",
        "PermissionError": "You do not have permission to access this resource",
        "FileNotFoundError": "Requested resource not found",
        "ValueError": "Invalid value provided",
        "KeyError": "Configuration error",
        "ImportError": "Service error",
        "TypeError": "Type error in request",
    }

    @staticmethod
    def sanitize_error(error: Exception, debug: bool = False) -> Dict[str, Any]:
        """
        Convert exception to safe error response.

        Args:
            error: The exception that occurred
            debug: If True, include stack trace (only in debug mode)

        Returns:
            Safe error dictionary
        """
        error_type = type(error).__name__

        # Get safe message
        safe_message = ErrorSanitizer.ERROR_MESSAGES.get(
            error_type,
            "An error occurred processing your request"
        )

        response = {
            "error": safe_message,
            "type": error_type if debug else "Error",
            "timestamp": datetime.utcnow().isoformat(),
        }

        # Only include trace in debug mode
        if debug:
            import traceback
            response["traceback"] = traceback.format_exc()

        logger.error(f"Error ({error_type}): {str(error)}")

        return response


from starlette.middleware.base import BaseHTTPMiddleware

class SecurityMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware for security checks."""

    def __init__(self, app, rate_limiter: Optional[RateLimiter] = None):
        """Initialize middleware."""
        super().__init__(app)
        self.rate_limiter = rate_limiter or RateLimiter()
        self.validator = RequestValidator()

    async def dispatch(self, request: Request, call_next: Callable) -> Any:
        """Process request through security checks."""
        # Extract user ID if available
        user_id = None
        if "user" in request.scope:
            user_id = getattr(request.scope["user"], "id", None)

        # Apply rate limiting
        if user_id:
            is_limited, reason = self.rate_limiter.is_rate_limited(str(user_id))
            if is_limited:
                logger.warning(f"Rate limit hit for user {user_id}: {reason}")
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={"error": reason}
                )

        # Add security headers to response
        response = await call_next(request)

        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        # Relaxed CSP to allow FastAPI Swagger UI (served from CDN) and frontend
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "img-src 'self' data: https://fastapi.tiangolo.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "connect-src 'self' http://localhost:* ws://localhost:*"
        )

        return response


def require_https(func: Callable) -> Callable:
    """Decorator to enforce HTTPS in production."""
    @wraps(func)
    async def wrapper(request: Request, *args, **kwargs):
        # Allow localhost and non-production
        if os.getenv("ENVIRONMENT", "dev") == "prod":
            if request.url.scheme != "https":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="HTTPS is required"
                )
        return await func(request, *args, **kwargs)
    return wrapper


def sanitize_logs(message: str) -> str:
    """
    Sanitize log messages to remove sensitive information.

    Removes API keys, tokens, and passwords.
    """
    import re

    # Remove API keys
    message = re.sub(r"sk-[a-zA-Z0-9]{48}", "sk-***", message)
    message = re.sub(r"AIza[0-9A-Za-z\-_]{35}", "AIza***", message)

    # Remove JWT tokens
    message = re.sub(r"Bearer [a-zA-Z0-9\-_.]+", "Bearer ***", message)

    # Remove passwords
    message = re.sub(r"password['\"]?\s*:\s*['\"]?[^'\"}\s]+", 'password: "***"', message)

    return message
