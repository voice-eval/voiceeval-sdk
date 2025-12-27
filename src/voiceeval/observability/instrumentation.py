from functools import wraps
import asyncio
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

# Create a tracer for the library
tracer = trace.get_tracer("voiceeval.sdk")

def observe(name_override=None):
    """
    A decorator to capture traces. 
    Works with both sync and async functions.
    """
    def decorator(func):
        span_name = name_override or func.__name__
        
        if asyncio.iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                with tracer.start_as_current_span(span_name) as span:
                    try:
                        span.set_attribute("voiceeval.inputs", str(args)[:1000])
                        span.set_attribute("voiceeval.kwargs", str(kwargs)[:1000])
                        span.set_attribute("gen_ai.system", "voiceeval")
                        
                        result = await func(*args, **kwargs)
                        
                        span.set_attribute("voiceeval.output", str(result)[:1000])
                        return result
                    except Exception as e:
                        span.record_exception(e)
                        span.set_status(Status(StatusCode.ERROR))
                        raise
            return async_wrapper
        else:
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                with tracer.start_as_current_span(span_name) as span:
                    try:
                        span.set_attribute("voiceeval.inputs", str(args)[:1000])
                        span.set_attribute("voiceeval.kwargs", str(kwargs)[:1000])
                        span.set_attribute("gen_ai.system", "voiceeval")
                        
                        result = func(*args, **kwargs)
                        
                        span.set_attribute("voiceeval.output", str(result)[:1000])
                        return result
                    except Exception as e:
                        span.record_exception(e)
                        span.set_status(Status(StatusCode.ERROR))
                        raise
            return sync_wrapper
    return decorator
