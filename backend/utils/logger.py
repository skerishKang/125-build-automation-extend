"""Centralised logging utilities."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Iterable, Optional


LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)


def configure_logging(*, level: int = logging.INFO, handlers: Optional[Iterable[logging.Handler]] = None) -> None:
    """Configure root logging for the backend.

    Existing handlers are cleared to avoid duplicate messages when the
    function is called multiple times (for example during tests).
    """

    if handlers is None:
        handlers = [
            RotatingFileHandler(LOG_DIR / "backend.log", maxBytes=5_000_000, backupCount=3, encoding="utf-8"),
            logging.StreamHandler(),
        ]

    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)

    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    for handler in handlers:
        handler.setFormatter(formatter)
        root_logger.addHandler(handler)


__all__ = ["configure_logging"]
