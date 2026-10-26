"""Utility functions for retrieving school settings."""

from django.core.cache import cache
from core.models import SchoolSettings


def get_school_settings(school):
    """
    Get school settings, using cache for performance.
    Falls back to defaults if settings don't exist.
    """
    cache_key = f"school_settings_{school.id}"

    # Try to get from cache
    settings = cache.get(cache_key)
    if settings:
        return settings

    # Get or create settings
    settings, _ = SchoolSettings.objects.get_or_create(school=school)

    # Cache for 1 hour
    cache.set(cache_key, settings, 3600)

    return settings


def invalidate_school_settings_cache(school):
    """Invalidate the settings cache for a school."""
    cache_key = f"school_settings_{school.id}"
    cache.delete(cache_key)
