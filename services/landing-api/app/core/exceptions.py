from __future__ import annotations


class BrewBeanError(Exception):
    """Base exception for BREW & BEAN Landing API."""


class ResourceNotFoundError(BrewBeanError):
    """Raised when a requested store, product, or session is not found."""


class OllamaUnavailableError(BrewBeanError):
    """Raised when Ollama local node is unreachable or circuit breaker is open."""
