from __future__ import annotations

from app.core.exceptions import BrewBeanError


class IngestionError(BrewBeanError):
    """Raised when loading, chunking, or embedding knowledge documents fails."""
