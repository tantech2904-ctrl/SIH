__version__ = "1.0.0"
def available_adapter_names() -> list[str]:
    """Names of every adapter this host *could* run, based on OS.

    This does not call is_available() on each adapter — some adapters
    may exist on this OS but be temporarily unavailable (file missing,
    missing optional dependency). This is the *capability* list the
    connector reports to the backend so the UI knows what toggles to
    show.
    """
    return [cls.name for cls in _all_adapter_classes()]


__all__ = ["BaseAdapter", "Event", "build_adapters", "available_adapter_names"]