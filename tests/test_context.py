"""Unit tests for voiceeval.context — Call ID management."""

import asyncio
import uuid
from unittest.mock import patch

import pytest

from voiceeval.context import (
    CallMetadata,
    _call_metadata_var,
    ensure_call_metadata,
    get_call_id,
    get_call_metadata,
    set_call_metadata,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _reset_context():
    """Reset the ContextVar so tests are isolated."""
    _call_metadata_var.set(None)


# ---------------------------------------------------------------------------
# CallMetadata dataclass
# ---------------------------------------------------------------------------

class TestCallMetadata:
    def test_generates_uuid_by_default(self):
        meta = CallMetadata()
        # Should be a valid UUID4 string
        parsed = uuid.UUID(meta.call_id, version=4)
        assert str(parsed) == meta.call_id

    def test_accepts_explicit_call_id(self):
        meta = CallMetadata(call_id="custom-id")
        assert meta.call_id == "custom-id"


# ---------------------------------------------------------------------------
# Context variable helpers
# ---------------------------------------------------------------------------

class TestGetCallMetadata:
    def setup_method(self):
        _reset_context()

    def test_returns_none_when_no_context(self):
        assert get_call_metadata() is None

    def test_returns_metadata_after_set(self):
        meta = CallMetadata(call_id="test-123")
        set_call_metadata(meta)
        assert get_call_metadata() is meta


class TestGetCallId:
    def setup_method(self):
        _reset_context()

    def test_returns_none_when_no_context(self):
        assert get_call_id() is None

    def test_returns_call_id_string(self):
        meta = CallMetadata(call_id="abc")
        set_call_metadata(meta)
        assert get_call_id() == "abc"


class TestEnsureCallMetadata:
    def setup_method(self):
        _reset_context()

    def test_creates_new_metadata_when_none(self):
        meta = ensure_call_metadata()
        assert isinstance(meta, CallMetadata)
        assert meta.call_id is not None

    def test_returns_same_metadata_on_second_call(self):
        first = ensure_call_metadata()
        second = ensure_call_metadata()
        assert first is second
        assert first.call_id == second.call_id

    def test_does_not_overwrite_existing(self):
        explicit = CallMetadata(call_id="explicit")
        set_call_metadata(explicit)
        result = ensure_call_metadata()
        assert result.call_id == "explicit"


# ---------------------------------------------------------------------------
# Async / nested decorator scenario
# ---------------------------------------------------------------------------

class TestCallIdConsistencyAcrossNestedCalls:
    """Simulate the main use-case: nested @observe-decorated functions
    should all see the same call_id."""

    def setup_method(self):
        _reset_context()

    @pytest.mark.anyio
    async def test_nested_async_functions_share_call_id(self):
        collected_ids: list[str] = []

        async def inner():
            meta = ensure_call_metadata()
            collected_ids.append(meta.call_id)

        async def outer():
            meta = ensure_call_metadata()
            collected_ids.append(meta.call_id)
            await inner()

        await outer()

        assert len(collected_ids) == 2
        assert collected_ids[0] == collected_ids[1], (
            "Nested calls must share the same call_id"
        )

    def test_nested_sync_functions_share_call_id(self):
        collected_ids: list[str] = []

        def inner():
            meta = ensure_call_metadata()
            collected_ids.append(meta.call_id)

        def outer():
            meta = ensure_call_metadata()
            collected_ids.append(meta.call_id)
            inner()

        outer()

        assert len(collected_ids) == 2
        assert collected_ids[0] == collected_ids[1]

    @pytest.mark.anyio
    async def test_separate_async_tasks_get_different_ids(self):
        """Different top-level asyncio tasks should have independent contexts."""
        ids: list[str] = []

        async def task():
            _reset_context()  # fresh context per task
            meta = ensure_call_metadata()
            ids.append(meta.call_id)

        await asyncio.gather(task(), task())

        assert len(ids) == 2
        assert ids[0] != ids[1], "Independent tasks must get unique call_ids"
