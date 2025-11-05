"""Main bot command registration."""

from telegram.ext import Application

from .handlers import register_handlers as register_main_bot_handlers

__all__ = ["register_main_bot_handlers"]
