"""Core application package.

This module will host the shared application wiring such as
initialising the Telegram application, background schedulers,
and dependency injection hooks.  Individual bot features live
under ``backend/bots`` and import shared services via this
package.
"""

from .application import build_application

__all__ = ["build_application"]
