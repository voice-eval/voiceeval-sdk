"""
Call context management for VoiceEval SDK.

Provides a centralized call ID that is shared across all spans
within the same execution context (asyncio task or thread).
Uses Python's contextvars for safe async/thread-local storage.
"""

import uuid
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Optional


_call_metadata_var: ContextVar[Optional["CallMetadata"]] = ContextVar(
    "voiceeval_call_metadata", default=None
)

_monitoring_skipped_var: ContextVar[bool] = ContextVar(
    "voiceeval_monitoring_skipped", default=False
)


@dataclass
class CallMetadata:
    """Metadata for the current call execution context.

    Attributes:
        call_id: A unique UUID string identifying this call.
                 Shared across every span in the same context.
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

    The first call in the chain creates the metadata;
    all subsequent ones reuse it.
    """
    meta = _call_metadata_var.get()
    if meta is None:
        meta = CallMetadata()
        _call_metadata_var.set(meta)
    return meta


def monitor_call() -> CallMetadata:
    """Explicitly opt this call into monitoring.

    Use when Client is configured with auto_monitor=False.
    Creates a call_id so spans are tagged and traces reach MongoDB/eval pipeline.
    """
    _monitoring_skipped_var.set(False)
    return ensure_call_metadata()


def skip_call() -> None:
    """Opt this call out of monitoring.

    Spans will still be exported to Langfuse but will NOT get a voiceeval.call_id,
    so they won't be written to MongoDB or trigger evaluations.
    """
    _monitoring_skipped_var.set(True)


def is_monitoring_skipped() -> bool:
    """Check if the current call has been opted out of monitoring."""
    return _monitoring_skipped_var.get()
