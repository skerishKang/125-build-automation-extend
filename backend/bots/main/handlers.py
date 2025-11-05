"""Main bot command registration helpers."""

from importlib import import_module
from typing import TYPE_CHECKING

from telegram.ext import Application, CommandHandler, MessageHandler, filters

if TYPE_CHECKING:  # pragma: no cover - for type hinting only
    from . import runtime as runtime_module


def _runtime():
    """Import the runtime module lazily to avoid circular imports."""

    return import_module("backend.bots.main.handlers.runtime")


def register_handlers(app: Application) -> Application:
    """Register command and message handlers for the main bot."""

    runtime = _runtime()

    # Command handlers
    app.add_handler(CommandHandler("start", runtime.handle_start))
    app.add_handler(CommandHandler("list", runtime.handle_list))
    app.add_handler(CommandHandler("mode", runtime.handle_mode))

    app.add_handler(CommandHandler("drive", runtime.handle_drive))
    app.add_handler(CommandHandler("drivelist", runtime.handle_drive_list))
    app.add_handler(CommandHandler("driveget", runtime.handle_drive_get))
    app.add_handler(CommandHandler("drivesync", runtime.handle_drive_sync))

    app.add_handler(CommandHandler("gmail_on", runtime.handle_gmail_on))
    app.add_handler(CommandHandler("gmail_off", runtime.handle_gmail_off))
    app.add_handler(CommandHandler("gmail_status", runtime.handle_gmail_status))
    app.add_handler(CommandHandler("gmail_list", runtime.handle_gmail_list))
    app.add_handler(CommandHandler("gmail_reply", runtime.handle_gmail_reply))
    app.add_handler(CommandHandler("gmail_recent", runtime.handle_gmail_recent))

    app.add_handler(CommandHandler("cal_on", runtime.handle_cal_on))
    app.add_handler(CommandHandler("cal_off", runtime.handle_cal_off))
    app.add_handler(CommandHandler("cal_status", runtime.handle_cal_status))
    app.add_handler(CommandHandler("cal_today", runtime.handle_cal_today))
    app.add_handler(CommandHandler("cal_tomorrow", runtime.handle_cal_tomorrow))
    app.add_handler(CommandHandler("cal_week", runtime.handle_cal_week))
    app.add_handler(CommandHandler("cal_search", runtime.handle_cal_search))

    # Message handlers
    app.add_handler(MessageHandler(filters.Document.ALL, runtime.handle_document_auto_save))
    app.add_handler(MessageHandler(filters.PHOTO, runtime.handle_photo))
    app.add_handler(MessageHandler(filters.VOICE, runtime.handle_voice))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, runtime.handle_text))

    return app
