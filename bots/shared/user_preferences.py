"""
User Preferences Storage - Redis-backed settings for hybrid automation modes.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict

from .redis_utils import REDIS_ENABLED, redis_client

logger = logging.getLogger("user_preferences")

PREFERENCE_KEY_PREFIX = "user_prefs:"
DEFAULT_PREFERENCES = {
    "mode": "ask",  # ask | auto | skip
    "default_actions": {
        "document": "none",
        "image": "none",
        "audio": "none",
    },
}


class PreferenceStore:
    """Simple key/value preference store with Redis backing."""

    def __init__(self, prefix: str = PREFERENCE_KEY_PREFIX):
        self.prefix = prefix
        # fallback in-memory cache when Redis is disabled
        self._memory_store: Dict[str, Dict[str, str]] = {}

    def _make_key(self, chat_id: str) -> str:
        return f"{self.prefix}{chat_id}"

    def get_preferences(self, chat_id: str) -> Dict[str, Any]:
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

        merged: Dict[str, Any] = {**DEFAULT_PREFERENCES, **stored}

        # Backward compatibility: migrate legacy "default_action" field
        legacy_action = stored.get("default_action") if isinstance(stored, dict) else None
        default_actions = DEFAULT_PREFERENCES["default_actions"].copy()
        stored_defaults = stored.get("default_actions") if isinstance(stored, dict) else {}
        if isinstance(stored_defaults, dict):
            default_actions.update(stored_defaults)
        if isinstance(legacy_action, str):
            default_actions["document"] = legacy_action
        merged["default_actions"] = default_actions

        return merged

    def set_preferences(self, chat_id: str, prefs: Dict[str, Any]) -> Dict[str, Any]:
        """Persist provided preferences outside of defaults."""
        current = self.get_preferences(chat_id)
        merged: Dict[str, Any] = {**current}

        for key, value in prefs.items():
            if key == "default_actions":
                defaults = merged.get("default_actions", {}).copy()
                if isinstance(value, dict):
                    defaults.update(value)
                merged["default_actions"] = defaults
            else:
                merged[key] = value

        payload: Dict[str, Any] = {}
        for key, value in merged.items():
            default_value = DEFAULT_PREFERENCES.get(key)
            if key == "default_actions":
                diff = {
                    t: v
                    for t, v in value.items()
                    if default_value.get(t) != v  # type: ignore[arg-type]
                }
                if diff:
                    payload[key] = diff
            elif value != default_value:
                payload[key] = value
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

    def update_preference(self, chat_id: str, key: str, value: Any) -> Dict[str, Any]:
        """Update a single preference and return the new state."""
        current = self.get_preferences(chat_id)
        if key == "default_actions":
            if isinstance(value, dict):
                defaults = current.get("default_actions", {}).copy()
                defaults.update(value)
                current["default_actions"] = defaults
        else:
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
