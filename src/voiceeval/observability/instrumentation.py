from functools import wraps
import asyncio
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

from voiceeval.context import ensure_call_metadata

# Create a tracer for the library
tracer = trace.get_tracer("voiceeval.sdk")

def observe(name_override=None, rename_parent=False):
    """
    A decorator to capture traces.
    Works with both sync and async functions.
    
    Args:
        name_override: Optional name for the span. If not provided, uses the function name.
        rename_parent: If True, renames the current parent span instead of creating a new child span.
                      This is useful when used with decorators like LiveKit's @server.rtc_session()
                      that create their own spans (e.g., "job_entrypoint").
    
    Usage:
        # Create a new span with custom name:
        @observe(name_override="my-custom-span")
        async def my_function():
            ...
        
        # Rename the parent span (useful with LiveKit):
        @observe(name_override="my-agent", rename_parent=True)
        @server.rtc_session()
        async def my_agent(ctx: JobContext):
            ...
        
        # Or use decorator order to create child span inside LiveKit span:
        @server.rtc_session()
        @observe(name_override="my-agent")
        async def my_agent(ctx: JobContext):
            ...
    """
    def decorator(func):
        span_name = name_override or func.__name__
        
        if asyncio.iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                call_meta = ensure_call_metadata()
                should_rename = rename_parent
                current_span = trace.get_current_span()
                
                # Auto-detect if we are wrapped by a generic LiveKit span
                if name_override and not should_rename and current_span:
                    # Check if it's a recording span (real span)
                    if hasattr(current_span, "is_recording") and current_span.is_recording():
                         # Check for known generic entrypoint names
                        if current_span.name in ["job entrypoint", "job_entrypoint"]:
                             should_rename = True

                if should_rename and name_override:
                    # Rename the current (parent) span instead of creating a new one
                    if current_span and current_span.is_recording():
                        current_span.update_name(name_override)
                        current_span.set_attribute("voiceeval.trace_name_override", name_override) # Persist override
                        current_span.set_attribute("voiceeval.call_id", call_meta.call_id)
                        current_span.set_attribute("voiceeval.inputs", str(args))
                        current_span.set_attribute("voiceeval.kwargs", str(kwargs))
                        current_span.set_attribute("gen_ai.system", "voiceeval")
                        try:
                            result = await func(*args, **kwargs)
                            current_span.set_attribute("voiceeval.output", str(result))
                            return result
                        except Exception as e:
                            current_span.record_exception(e)
                            current_span.set_status(Status(StatusCode.ERROR))
                            raise
                    else:
                        # No valid parent span, fall through to create new span
                        pass
                
                # Default behavior: create a new child span
                with tracer.start_as_current_span(span_name) as span:
                    if name_override:
                        span.set_attribute("voiceeval.trace_name_override", name_override)
                    try:
                        span.set_attribute("voiceeval.call_id", call_meta.call_id)
                        span.set_attribute("voiceeval.inputs", str(args))
                        span.set_attribute("voiceeval.kwargs", str(kwargs))
                        span.set_attribute("gen_ai.system", "voiceeval")
                        
                        result = await func(*args, **kwargs)
                        
                        span.set_attribute("voiceeval.output", str(result))
                        return result
                    except Exception as e:
                        span.record_exception(e)
                        span.set_status(Status(StatusCode.ERROR))
                        raise
            return async_wrapper
        else:
            @wraps(func)
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                call_meta = ensure_call_metadata()
                should_rename = rename_parent
                current_span = trace.get_current_span()
                
                # Auto-detect if we are wrapped by a generic LiveKit span
                if name_override and not should_rename and current_span:
                    if hasattr(current_span, "is_recording") and current_span.is_recording():
                        if current_span.name in ["job entrypoint", "job_entrypoint"]:
                             should_rename = True

                if should_rename and name_override:
                    # Rename the current (parent) span instead of creating a new one
                    if current_span and current_span.is_recording():
                        current_span.update_name(name_override)
                        current_span.set_attribute("voiceeval.trace_name_override", name_override) # Persist override
                        current_span.set_attribute("voiceeval.call_id", call_meta.call_id)
                        current_span.set_attribute("voiceeval.inputs", str(args))
                        current_span.set_attribute("voiceeval.kwargs", str(kwargs))
                        current_span.set_attribute("gen_ai.system", "voiceeval")
                        try:
                            result = func(*args, **kwargs)
                            current_span.set_attribute("voiceeval.output", str(result))
                            return result
                        except Exception as e:
                            current_span.record_exception(e)
                            current_span.set_status(Status(StatusCode.ERROR))
                            raise
                    else:
                        # No valid parent span, fall through to create new span
                        pass
                
                # Default behavior: create a new child span
                with tracer.start_as_current_span(span_name) as span:
                    if name_override:
                        span.set_attribute("voiceeval.trace_name_override", name_override)
                    try:
                        span.set_attribute("voiceeval.call_id", call_meta.call_id)
                        span.set_attribute("voiceeval.inputs", str(args))
                        span.set_attribute("voiceeval.kwargs", str(kwargs))
                        span.set_attribute("gen_ai.system", "voiceeval")
                        
                        result = func(*args, **kwargs)
                        
                        span.set_attribute("voiceeval.output", str(result))
                        return result
                    except Exception as e:
                        span.record_exception(e)
                        span.set_status(Status(StatusCode.ERROR))
                        raise
            return sync_wrapper
    return decorator
