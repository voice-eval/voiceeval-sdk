import os
import logging
from typing import Optional, List, Callable, Sequence
from voiceeval.models import Call
from voiceeval.observability.exporters import PostProcessingSpanExporter, enforce_name_override
from voiceeval.observability.processor import CallIdSpanProcessor
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry import trace
import httpx

logger = logging.getLogger(__name__)

class Client:
    """
    Main entry point for the VoiceEval SDK.

    Minimal setup::

        from voiceeval import Client
        client = Client(api_key="ve_xxx", agent_name="my-booking-agent")

    All LLM calls and LiveKit spans are automatically traced and exported.
    No ``@observe`` decorator or ``client.flush()`` required — OTel flushes
    on process exit automatically.
    """
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://api.voiceeval.com/v1/traces",
        agent_name: Optional[str] = None,
        auto_monitor: bool = True,
        sample_rate: float = 1.0,
        span_post_processors: Optional[List[Callable[[Sequence[ReadableSpan]], None]]] = None,
    ):
        self.api_key = api_key or os.environ.get("VOICE_EVAL_API_KEY")
        if not self.api_key:
            raise ValueError("API Key is required. Set VOICE_EVAL_API_KEY env var or pass in __init__.")

        self.ingest_url = base_url
        self.agent_name = agent_name
        self.auto_monitor = auto_monitor
        self.sample_rate = sample_rate

        self._validate_api_key()
        self.enable_observability(span_post_processors)

    def _validate_api_key(self):
        """Checks if the API key is valid by calling the server."""
        if "/v1/traces" in self.ingest_url:
            validate_url = self.ingest_url.replace("/v1/traces", "/v1/auth/validate")
        else:
            validate_url = self.ingest_url.replace("/traces", "/auth/validate")

        try:
            response = httpx.get(
                validate_url,
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=5.0
            )
            if response.status_code == 403:
                raise ValueError("Invalid API Key provided to VoiceEval Client.")
            elif response.status_code == 404:
                logger.warning("VoiceEval Server does not support API key validation (Endpoint not found). Ensure server is updated.")
            elif response.status_code != 200:
                logger.warning(f"Could not validate API key (Status {response.status_code}). Proceeding, but exports may fail.")
        except Exception as e:
            if "Invalid API Key" in str(e):
                raise e
            logger.warning(f"Failed to reach VoiceEval server for validation: {e}")

    def enable_observability(self, span_post_processors: Optional[List[Callable[[Sequence[ReadableSpan]], None]]] = None):
        """Auto-configures OTel to send data to VoiceEval and instruments common libraries."""
        # shutdown_on_exit=True (default) registers atexit handler — auto-flush on exit
        provider = TracerProvider()

        # CallIdSpanProcessor runs FIRST on every span start — attaches call_id + agent_name
        provider.add_span_processor(
            CallIdSpanProcessor(
                agent_name=self.agent_name,
                auto_monitor=self.auto_monitor,
                sample_rate=self.sample_rate,
            )
        )

        exporter = OTLPSpanExporter(
            endpoint=self.ingest_url,
            headers={"Authorization": f"Bearer {self.api_key}"}
        )

        post_processors = list(span_post_processors) if span_post_processors else []
        if enforce_name_override not in post_processors:
            post_processors.append(enforce_name_override)

        exporter = PostProcessingSpanExporter(exporter, post_processors)
        provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(provider)

        self._instrument_libraries(provider)

    def _instrument_livekit(self, provider):
        """Attempts to configure LiveKit Agents to use the same TracerProvider."""
        try:
            from livekit.agents import telemetry
            telemetry.set_tracer_provider(provider)
            logger.debug("Successfully instrumented LiveKit Agents.")
        except ImportError:
            logger.debug("LiveKit Agents not installed, skipping instrumentation.")
        except Exception as e:
            logger.warning(f"Failed to instrument LiveKit Agents: {e}")

    def _instrument_libraries(self, provider):
        """Auto-instrument all installed OTel instrumentation packages and LiveKit."""
        try:
            from importlib.metadata import entry_points
        except ImportError:
            return

        logger.debug("Auto-instrumenting installed libraries...")
        eps = entry_points(group="opentelemetry_instrumentor")

        for entry_point in eps:
            try:
                instrumentor = entry_point.load()()
                if not instrumentor.is_instrumented_by_opentelemetry:
                    instrumentor.instrument()
                    logger.debug(f"Instrumented: {entry_point.name}")
            except ImportError:
                logger.debug(f"{entry_point.name} not installed, skipping.")
            except Exception as e:
                logger.debug(f"Could not instrument {entry_point.name}: {e}")

        self._instrument_livekit(provider)

    def flush(self):
        """Force flush all buffered traces to the backend.

        Note: OTel automatically flushes on process exit (via atexit handler).
        You only need to call this if you want to force an immediate flush
        mid-execution.
        """
        provider = trace.get_tracer_provider()
        if hasattr(provider, "force_flush"):
            provider.force_flush()
