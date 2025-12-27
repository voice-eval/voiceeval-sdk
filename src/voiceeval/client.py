import os
import logging
from typing import Optional
from voiceeval.models import Call
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry import trace
import httpx

logger = logging.getLogger(__name__)

class Client:
    """
    Main entry point for the VoiceEval SDK.
    """
    def __init__(self, api_key: Optional[str] = None, base_url: str = "https://api.voiceeval.com/v1/traces"):
        self.api_key = api_key or os.environ.get("VOICE_EVAL_API_KEY")
        if not self.api_key:
            raise ValueError("API Key is required. Set VOICE_EVAL_API_KEY env var or pass in __init__.")
            
        self.ingest_url = base_url
        
        # Validate API Key
        self._validate_api_key()
        
        self.enable_observability()

    def _validate_api_key(self):
        """Checks if the API key is valid by calling the server."""
        # Assume base_url ends with /v1/traces or similar
        # Construct validation URL: replace /traces with /auth/validate, or just appending to root
        # Ideally, we'd have a clean base URL. For now, hacky replacement to match default behaviour.
        
        if "/v1/traces" in self.ingest_url:
            validate_url = self.ingest_url.replace("/v1/traces", "/v1/auth/validate")
        else:
            # Fallback or smart guess? 
            # If user passes just http://localhost:8000, we might need /v1/auth/validate
            # If user passes http://localhost:8000/v1, we need /auth/validate
            # For this task, let's assume the standard structure.
             validate_url = self.ingest_url.replace("/traces", "/auth/validate") # Attempt to handle /v1/traces -> /v1/auth/validate

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
            # Don't crash for network errors, just warn, unless it's explicitly Invalid API Key error raised above
            if "Invalid API Key" in str(e):
                raise e
            logger.warning(f"Failed to reach VoiceEval server for validation: {e}")


    def enable_observability(self):
        """Auto-configures OTel to send data to VoiceEval Proxy and instruments common libraries."""
        provider = TracerProvider()
        exporter = OTLPSpanExporter(
            endpoint=self.ingest_url,
            headers={"Authorization": f"Bearer {self.api_key}"}
        )
        
        provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(provider)
        
        # Auto-instrument common libraries
        self._instrument_libraries()

    def create_call(self, agent_id: str) -> Call:
        """
        Initialize a tracking object for a new call.
        """
        raise NotImplementedError("create_call is not implemented yet")

    def log_call(self, call: Call) -> None:
        """
        Log a completed call to the platform.
        """
        tracer = trace.get_tracer("voiceeval.sdk")
        with tracer.start_as_current_span("log_call") as span:
            span.set_attribute("call.id", call.call_id)
            span.set_attribute("agent.id", call.agent_id)

    def _instrument_libraries(self):
        """
        Auto-instrument all installed OTel instrumentation packages.
        This uses the standard 'opentelemetry_instrumentor' entry point.
        """
        try:
            from importlib.metadata import entry_points
        except ImportError:
            return

        logger.debug("Auto-instrumenting installed libraries...")
        # Python 3.10+ supports filtering by group
        eps = entry_points(group="opentelemetry_instrumentor")
        
        for entry_point in eps:
            try:
                instrumentor = entry_point.load()()
                if not instrumentor.is_instrumented_by_opentelemetry:
                    instrumentor.instrument()
                    logger.debug(f"Instrumented: {entry_point.name}")
            except Exception as e:
                # Silently fail (debug log only)
                logger.debug(f"Failed to instrument {entry_point.name}: {e}")

if __name__ == "__main__":
    # Configure logging to see output when running this script directly
    # logging.basicConfig(level=logging.DEBUG)
    
    # Client() automatically enables observability and instruments libraries
    # Using a dummy key for testing initialization
    try:
        client = Client(api_key="test_key")
        print("Client initialized and libraries instrumented.")
    except Exception as e:
        print(f"Initialization failed: {e}")