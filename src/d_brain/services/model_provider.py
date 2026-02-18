"""Runtime model-provider state service (in-process singleton)."""

from typing import Final

PROVIDER_LABELS: Final[dict[str, str]] = {
    "openai-cli": "🤖 GPT (CLI)",
    "claude-cli": "🧠 Claude (CLI)",
    "openai-api": "🤖 GPT (API)",
}

VALID_PROVIDERS: Final[frozenset[str]] = frozenset(PROVIDER_LABELS)

_active_provider: str | None = None


def get_active_provider(settings_default: str) -> str:
    """Return the runtime-selected provider, falling back to *settings_default*."""
    if _active_provider is not None:
        return _active_provider
    return settings_default


def set_active_provider(provider: str) -> str:
    """Set *provider* as the active one.  Returns the human-readable label."""
    global _active_provider  # noqa: PLW0603
    if provider not in VALID_PROVIDERS:
        raise ValueError(f"Invalid provider: {provider!r}. Valid: {', '.join(sorted(VALID_PROVIDERS))}")
    _active_provider = provider
    return PROVIDER_LABELS[provider]


def get_provider_label(provider: str) -> str:
    """Human-readable label for *provider*."""
    return PROVIDER_LABELS.get(provider, provider)
