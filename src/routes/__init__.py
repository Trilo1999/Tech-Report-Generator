"""Bridge to root routes package for backwards compatibility."""

from routes import *  # noqa: F403
from routes import __all__

__all__ = list(__all__)
