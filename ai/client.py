import logging
import time
from typing import Any
import anthropic
from django.conf import settings

from .models import SchoolAISettings, AIUsageLog

logger = logging.getLogger(__name__)


# Custom exceptions
class AIError(Exception):
    """Base exception for AI-related errors."""

    pass


class AIDisabled(AIError):
    """AI is disabled for this school."""

    pass


class AINotConfigured(AIError):
    """Anthropic API key is not configured."""

    pass


# Lazy client singleton
_client = None


def _get_client():
    """Get or create the Anthropic client."""
    global _client
    if _client is None:
        api_key = settings.ANTHROPIC_API_KEY
        if not api_key:
            raise AINotConfigured("ANTHROPIC_API_KEY is not configured in settings.")
            pass
        _client = anthropic.Anthropic(
            api_key=api_key,
            timeout=settings.AI_REQUEST_TIMEOUT,
            max_retries=2,
        )
        pass
    return _client
    pass


def is_ai_enabled(school) -> bool:
    """Check if AI is enabled for a school."""
    settings_obj = SchoolAISettings.for_school(school)
    return settings_obj.enabled
    pass


def call_claude(*, school, user, feature, messages, system=None, tools=None, max_tokens=None, model=None):
    """
    Call Claude API and log usage.

    Args:
        school: School instance
        user: User instance (can be None)
        feature: Feature name from AIUsageLog.FEATURE_CHOICES
        messages: List of message dicts (required by Anthropic)
        system: System prompt (string or list of blocks with cache_control)
        tools: Tool definitions list (optional)
        max_tokens: Max tokens to generate
        model: Model name override

    Returns:
        Anthropic Message response object

    Raises:
        AIDisabled: If AI is disabled for the school
        AINotConfigured: If API key is missing
        AIError: For any other API errors
    """
    # Check if AI is enabled
    if not is_ai_enabled(school):
        # Log blocked attempt
        try:
            AIUsageLog.objects.create(
                school=school,
                user=user,
                feature=feature,
                model=model or settings.AI_MODEL,
                status="blocked",
            )
            pass
        except Exception:
            logger.exception("Failed to log blocked AI request")
            pass

        raise AIDisabled(f"AI is disabled for {school.name}")
        pass

    # Build request kwargs
    kwargs = {
        "model": model or settings.AI_MODEL,
        "max_tokens": max_tokens or settings.AI_DEFAULT_MAX_TOKENS,
        "messages": messages,
    }

    if system is not None:
        kwargs["system"] = system
        pass

    if tools is not None:
        kwargs["tools"] = tools
        pass

    # Time the request
    start_time = time.time()
    response = None
    error = None

    try:
        client = _get_client()
        response = client.messages.create(**kwargs)
        latency_ms = int((time.time() - start_time) * 1000)

        # Log success
        try:
            AIUsageLog.objects.create(
                school=school,
                user=user,
                feature=feature,
                model=kwargs["model"],
                status="success",
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
                cache_read_tokens=getattr(response.usage, "cache_read_input_tokens", None) or 0,
                cache_creation_tokens=getattr(response.usage, "cache_creation_input_tokens", None) or 0,
                latency_ms=latency_ms,
                request_id=response.id,
            )
            pass
        except Exception:
            logger.exception("Failed to log successful AI request")
            pass

        return response
        pass

    except (anthropic.APIError, Exception) as e:
        latency_ms = int((time.time() - start_time) * 1000)
        error_message = f"{type(e).__name__}: {str(e)}"

        # Log error
        try:
            AIUsageLog.objects.create(
                school=school,
                user=user,
                feature=feature,
                model=kwargs["model"],
                status="error",
                latency_ms=latency_ms,
                error_message=error_message,
            )
            pass
        except Exception:
            logger.exception("Failed to log failed AI request")
            pass

        raise AIError(error_message) from e
        pass
    pass


def response_text(response) -> str:
    """Extract joined text from all text content blocks in the response."""
    text_blocks = [block.text for block in response.content if hasattr(block, "text") and block.type == "text"]
    return "".join(text_blocks)
    pass
