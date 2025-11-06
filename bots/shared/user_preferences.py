"""
User Preferences Storage - Redis-backed settings for hybrid automation modes.
"""
from __future__ import annotations

import json
import logging
from typing import Dict

from .redis_utils import REDIS_ENABLED, redis_client

logger = logging.getLogger("user_preferences")

PREFERENCE_KEY_PREFIX = "user_prefs:"
DEFAULT_PREFERENCES: Dict[str, str] = {
    "mode": "ask",           # ask | auto | skip
    "default_action": "none"  # none | drive | notion
}


class PreferenceStore:
    """Simple key/value preference store with Redis backing."""

    def __init__(self, prefix: str = PREFERENCE_KEY_PREFIX):
        self.prefix = prefix
        # fallback in-memory cache when Redis is disabled
        self._memory_store: Dict[str, Dict[str, str]] = {}

    def _make_key(self, chat_id: str) -> str:
        return f"{self.prefix}{chat_id}"

    def get_preferences(self, chat_id: str) -> Dict[str, str]:
        """Return stored preferences merged with defaults."""
        key = self._make_key(chat_id)

        if REDIS_ENABLED and redis_client:
            try:
                raw = redis_client.get(key)
                if raw:
                    stored = json.loads(raw)
                else:
                    stored = {}
            except Exception as exc:
                logger.error("Failed to read preferences for %s: %s", chat_id, exc)
                stored = {}
        else:
            stored = self._memory_store.get(chat_id, {})

        merged = {**DEFAULT_PREFERENCES, **stored}
        return merged

    def set_preferences(self, chat_id: str, prefs: Dict[str, str]) -> Dict[str, str]:
        """Persist provided preferences outside of defaults."""
        merged = {**DEFAULT_PREFERENCES, **prefs}
        payload = {k: v for k, v in merged.items() if DEFAULT_PREFERENCES.get(k) != v}
        key = self._make_key(chat_id)

        if REDIS_ENABLED and redis_client:
            try:
                redis_client.set(key, json.dumps(payload))
                return merged
            except Exception as exc:
                logger.error("Failed to save preferences for %s: %s", chat_id, exc)

        # fallback to in-memory storage if Redis failed or disabled
        self._memory_store[chat_id] = payload
        return merged

    def update_preference(self, chat_id: str, key: str, value: str) -> Dict[str, str]:
        """Update a single preference and return the new state."""
        current = self.get_preferences(chat_id)
        current[key] = value
        self.set_preferences(chat_id, current)
        return current

    def reset_preferences(self, chat_id: str) -> Dict[str, str]:
        """Reset preferences back to defaults."""
        if REDIS_ENABLED and redis_client:
            try:
                redis_client.delete(self._make_key(chat_id))
            except Exception as exc:
                logger.error("Failed to reset preferences for %s: %s", chat_id, exc)
        self._memory_store.pop(chat_id, None)
        return DEFAULT_PREFERENCES.copy()


# shared singleton instance
preference_store = PreferenceStore()
