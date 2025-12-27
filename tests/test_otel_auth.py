import pytest
from unittest.mock import patch
from voiceeval import Client
from voiceeval.observability import observe
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

def test_client_enables_otel():
    with patch("voiceeval.client.OTLPSpanExporter") as MockExporter:
        with patch("voiceeval.client.BatchSpanProcessor") as MockProcessor:
            with patch("voiceeval.client.TracerProvider") as MockProvider:
                # Mock trace.set_tracer_provider
                with patch("opentelemetry.trace.set_tracer_provider") as mock_set_provider:
                    
                    # Prevent auto-instrumentation from actually running during test
                    with patch("voiceeval.client.Client._instrument_libraries"):
                        client = Client(api_key="test_key")
                    
                    # Verify Exporter init
                    MockExporter.assert_called_with(
                        endpoint="https://api.voiceeval.com/v1/traces",
                        headers={"Authorization": "Bearer test_key"}
                    )
                    
                    # Verify Provider setup
                    mock_set_provider.assert_called()

def test_observe_decorator():
    # Setup a key-memory exporter for testing
    provider = TracerProvider()
    exporter = InMemorySpanExporter()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    test_tracer = provider.get_tracer("test_tracer")
    
    # Patch the global tracer used in the decorator module
    # We must patch where it is DEFINED (instrumentation.py), not where it is imported
    with patch("voiceeval.observability.instrumentation.tracer", test_tracer):
        
        @observe(name_override="test_span")
        def my_function(x):
            return x * 2
            
        result = my_function(5)
        assert result == 10
        
        spans = exporter.get_finished_spans()
        assert len(spans) == 1
        assert spans[0].name == "test_span"
        assert spans[0].attributes["voiceeval.inputs"] == "(5,)"
        assert spans[0].attributes["voiceeval.output"] == "10"
        assert spans[0].attributes["gen_ai.system"] == "voiceeval"
