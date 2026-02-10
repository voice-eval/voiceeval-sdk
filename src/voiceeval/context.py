"""
Call context management for VoiceEval SDK.

Provides a centralized call ID that is shared across all @observe-decorated
functions within the same execution context (asyncio task or thread).
Uses Python's contextvars for safe async/thread-local storage.
"""

import uuid
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Optional


# ContextVar holding the current CallMetadata for this execution context.
_call_metadata_var: ContextVar[Optional["CallMetadata"]] = ContextVar(
    "voiceeval_call_metadata", default=None
)

@dataclass
class CallMetadata:
    """Metadata for the current call execution context.

    Attributes:
        call_id: A unique UUID string identifying this call.
                 Shared across every @observe span in the same context.
    """

    call_id: str = field(default_factory=lambda: str(uuid.uuid4()))


def get_call_metadata() -> Optional[CallMetadata]:
    """Return the current CallMetadata, or None if no call is active."""
    return _call_metadata_var.get()


def get_call_id() -> Optional[str]:
    """Return the current call_id string, or None if no call is active."""
    meta = _call_metadata_var.get()
    return meta.call_id if meta else None


def set_call_metadata(metadata: CallMetadata) -> None:
    """Explicitly set the CallMetadata for this context."""
    _call_metadata_var.set(metadata)


def ensure_call_metadata() -> CallMetadata:
    """Return existing CallMetadata or create a new one.

    This is the primary entry point used by the @observe decorator.
    The first decorated function in the call chain creates the metadata;
    all subsequent ones reuse it.
    """
    meta = _call_metadata_var.get()
    if meta is None:
        meta = CallMetadata()
        _call_metadata_var.set(meta)
    return meta
