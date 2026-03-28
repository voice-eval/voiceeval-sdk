"""
CallIdSpanProcessor — automatically injects voiceeval.call_id into every span.

When a root span (e.g. LiveKit's "job_entrypoint") starts, a new call_id UUID
is generated and stored in a contextvar. All child spans within that execution
context inherit the same call_id.

This means customers get full trace linkage just by initializing the Client,
without needing to use the @observe decorator.
"""

import logging
from typing import Optional

from opentelemetry.context import Context
from opentelemetry.sdk.trace import Span, SpanProcessor

from voiceeval.context import (
    CallMetadata,
    ensure_call_metadata,
    is_monitoring_skipped,
    set_call_metadata,
)

logger = logging.getLogger(__name__)

_ROOT_SPAN_NAMES = frozenset({"job_entrypoint", "job entrypoint"})


class CallIdSpanProcessor(SpanProcessor):
    """SpanProcessor that attaches voiceeval.call_id to every span.

    On root spans (job_entrypoint): generates a fresh call_id.
    On all other spans: reuses the call_id from the current context,
    or generates one if none exists yet.

    Args:
        agent_name: Optional agent name to attach to every span.
        auto_monitor: If True (default), every call gets a call_id.
                      If False, only calls where monitor_call() was invoked.
        sample_rate: Float 0.0-1.0. Fraction of calls to monitor (default 1.0).
    """

    def __init__(
        self,
        agent_name: Optional[str] = None,
        auto_monitor: bool = True,
        sample_rate: float = 1.0,
    ):
        self._agent_name = agent_name
        self._auto_monitor = auto_monitor
        self._sample_rate = max(0.0, min(1.0, sample_rate))

    def _should_monitor(self) -> bool:
        """Decide whether the current call should be monitored."""
        if is_monitoring_skipped():
            return False

        if not self._auto_monitor:
            # In manual mode, only monitor if monitor_call() was invoked
            from voiceeval.context import get_call_metadata
            return get_call_metadata() is not None

        if self._sample_rate < 1.0:
            import random
            return random.random() < self._sample_rate

        return True

    def on_start(self, span: Span, parent_context: Optional[Context] = None) -> None:
        is_root = span.name in _ROOT_SPAN_NAMES

        if is_root:
            # New call — reset context and mint fresh call_id
            if self._should_monitor():
                meta = CallMetadata()
                set_call_metadata(meta)
            else:
                # Not monitoring this call — clear any stale metadata
                set_call_metadata(None)  # type: ignore[arg-type]
                return

        # Get or create metadata for this context
        from voiceeval.context import get_call_metadata
        meta = get_call_metadata()

        if meta is None:
            # No root span was seen yet (non-LiveKit usage, or auto_monitor=False
            # and monitor_call() wasn't called). Skip tagging.
            if not self._auto_monitor:
                return
            # For auto_monitor=True without a root span, create metadata
            meta = ensure_call_metadata()

        span.set_attribute("voiceeval.call_id", meta.call_id)
        span.set_attribute("gen_ai.system", "voiceeval")

        if self._agent_name:
            span.set_attribute("voiceeval.agent_name", self._agent_name)

    def on_end(self, span) -> None:
        pass

    def shutdown(self) -> None:
        pass

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        return True
