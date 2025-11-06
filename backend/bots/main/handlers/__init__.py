"""Handler exports for the main bot."""

from .runtime import (
    handle_start,
    handle_mode,
    handle_text,
    handle_photo,
    handle_voice,
    handle_list,
    handle_drive,
    handle_drive_list,
    handle_drive_get,
    handle_drive_sync,
    handle_gmail_on,
    handle_gmail_off,
    handle_gmail_status,
    handle_gmail_list,
    handle_cal_on,
    handle_cal_off,
    handle_cal_status,
    handle_cal_today,
    handle_cal_tomorrow,
    handle_cal_week,
    handle_cal_search,
    handle_document_auto_save,
)


def register_handlers(app):
    """Register all handlers with the Telegram application."""
    from telegram.ext import CommandHandler, MessageHandler, filters

    # Command handlers
    app.add_handler(CommandHandler("start", handle_start))
    app.add_handler(CommandHandler("mode", handle_mode))
    app.add_handler(CommandHandler("list", handle_list))
    app.add_handler(CommandHandler("drive", handle_drive))
    app.add_handler(CommandHandler("drivelist", handle_drive_list))
    app.add_handler(CommandHandler("driveget", handle_drive_get))
    app.add_handler(CommandHandler("drivesync", handle_drive_sync))
    app.add_handler(CommandHandler("gmail_on", handle_gmail_on))
    app.add_handler(CommandHandler("gmail_off", handle_gmail_off))
    app.add_handler(CommandHandler("gmail_status", handle_gmail_status))
    app.add_handler(CommandHandler("gmail_list", handle_gmail_list))
    app.add_handler(CommandHandler("cal_on", handle_cal_on))
    app.add_handler(CommandHandler("cal_off", handle_cal_off))
    app.add_handler(CommandHandler("cal_status", handle_cal_status))
    app.add_handler(CommandHandler("cal_today", handle_cal_today))
    app.add_handler(CommandHandler("cal_tomorrow", handle_cal_tomorrow))
    app.add_handler(CommandHandler("cal_week", handle_cal_week))
    app.add_handler(CommandHandler("cal_search", handle_cal_search))

    # Message handlers
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document_auto_save))


__all__ = [
    "register_handlers",
    "handle_start",
    "handle_mode",
    "handle_text",
    "handle_photo",
    "handle_voice",
    "handle_list",
    "handle_drive",
    "handle_drive_list",
    "handle_drive_get",
    "handle_drive_sync",
    "handle_gmail_on",
    "handle_gmail_off",
    "handle_gmail_status",
    "handle_gmail_list",
    "handle_cal_on",
    "handle_cal_off",
    "handle_cal_status",
    "handle_cal_today",
    "handle_cal_tomorrow",
    "handle_cal_week",
    "handle_cal_search",
    "handle_document_auto_save",
]
