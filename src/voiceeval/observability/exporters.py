import typing
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult

class PostProcessingSpanExporter(SpanExporter):
    """
    A SpanExporter that runs a list of post-processing functions on spans 
    before delegating them to another exporter.
    """
    
    def __init__(
        self, 
        delegate: SpanExporter, 
        post_processors: typing.List[typing.Callable[[typing.Sequence[ReadableSpan]], None]]
    ):
        """
        Args:
            delegate: The actual exporter to send spans to after processing.
            post_processors: A list of callables. Each callable receives the list of spans.
                             It can modify them in place or perform side effects (logging, validation).
        """
        self.delegate = delegate
        self.post_processors = post_processors

    def export(self, spans: typing.Sequence[ReadableSpan]) -> SpanExportResult:
        # Run all post-processors
        for processor in self.post_processors:
            try:
                processor(spans)
            except Exception:
                # We don't want a post-processor crash to stop the actual export
                # In a real system, we might log this.
                pass
        
        # Delegate to the real exporter
        return self.delegate.export(spans)

    def shutdown(self) -> None:
        self.delegate.shutdown()

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        return self.delegate.force_flush(timeout_millis)

import logging

logger = logging.getLogger(__name__)

def enforce_name_override(spans: typing.Sequence[ReadableSpan]) -> None:
    """
    Post-processor that checks if a span has the 'voiceeval.trace_name_override' attribute.
    If so, it forces the span name to match that attribute.
    This ensures that even if other instrumentations (like generic decorators or callbacks)
    renamed the span locally, our specific override takes precedence.
    """
    for span in spans:
        if "voiceeval.trace_name_override" in span.attributes:
            override_name = span.attributes["voiceeval.trace_name_override"]
            original_name = span.name
            
            logger.info(f"[VoiceEval] Found name override: '{override_name}' for span '{original_name}' (Trace ID: {span.context.trace_id:032x}, Span ID: {span.context.span_id:016x})")
            
            updated = False
            if hasattr(span, "update_name"):
                 # Check if we can check is_recording
                if hasattr(span, "is_recording") and span.is_recording():
                    span.update_name(override_name)
                    updated = True
                    logger.info(f"[VoiceEval] Updated span name using update_name(): {original_name} -> {override_name}")
            
            if not updated:
                # Forcefully update the name for export purposes
                # This works for the standard OTel SDK Span implementation
                try:
                    span._name = override_name
                    logger.info(f"[VoiceEval] Forcefully updated span._name: {original_name} -> {override_name}")
                except AttributeError:
                    # If it's some other Span implementation that doesn't use _name
                    # we might be out of luck, but standard Py SDK uses _name.
                    logger.warning(f"[VoiceEval] Failed to force update span name. implementation does not have _name attribute. Span type: {type(span)}")
                    pass

