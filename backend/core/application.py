"""Application bootstrap helpers.

The goal of this module is to provide a single entry-point for
building the Telegram application that wires together command
handlers, background tasks, and shared services.  The existing
``bot_runner.py`` script still owns the main runtime, but new
code should migrate towards using :func:`build_application`.
"""

from __future__ import annotations

from typing import Optional

from telegram.ext import Application


def build_application(token: str, *, name: Optional[str] = None) -> Application:
    """Create a Telegram ``Application`` instance.

    Parameters
    ----------
    token:
        Bot token used for authentication with the Telegram API.
    name:
        Optional application name.  When omitted the default from
        :mod:`python-telegram-bot` is used.

    Notes
    -----
    This helper intentionally keeps the configuration surface small.
    Complex handler wiring remains in ``bot_runner.py`` until it is
    gradually migrated into modular packages.
    """

    builder = Application.builder().token(token)
    if name:
        builder = builder.application_name(name)
    return builder.build()
