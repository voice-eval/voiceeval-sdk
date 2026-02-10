# Usage Guide

This guide provides comprehensive instructions on how to install, configure, and use the VoiceEval SDK for Python.

## Installation

Install the SDK using pip or uv:

```bash
pip install voiceeval-sdk
# or
uv add voiceeval-sdk
```

## Initialization

To start using the SDK, initialize the `Client` at the entry point of your application. This sets up the telemetry exporter and enables auto-instrumentation for supported LLM libraries.

```python
from voiceeval import Client

client = Client(
    project_name="my-voice-agent",
    api_key="your_api_key_here",
    base_url="https://api.voiceeval.com/v1/traces"
)
```

### Configuration via Environment Variables

You can configure the client using environment variables, avoiding hardcoded values in your code:

- `VOICE_EVAL_API_KEY`: Your API key.
- `VOICE_EVAL_BASE_URL`: The URL for the trace collector (default: `https://api.voiceeval.com/v1/traces`).
- `VOICE_EVAL_PROJECT_NAME`: The name of your project.

```python
# With environment variables set:
client = Client()
```

## Auto-Instrumentation

The SDK automatically instruments the following libraries if they are installed in your environment:

- OpenAI (`openai`)
- Anthropic (`anthropic`)
- Google Gemini (`google-generativeai`)
- Groq (`groq`)

No additional code is required to trace calls to these libraries. Once the `Client` is initialized, all requests and responses will be captured.

### Example: OpenAI

```python
from openai import OpenAI

# The client is already instrumented
client_openai = OpenAI()
response = client_openai.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": "Hello world"}]
)
```

## Manual Tracing with `@observe`

For functions that do not directly call LLMs but contain important logic (such as RAG retrieval, preprocessing, or agent orchestration), use the `@observe` decorator.

```python
from voiceeval import observe

@observe(name_override="document_retrieval")
def retrieve_documents(query: str):
    # Logic to retrieve documents
    return ["doc1", "doc2"]
```

### Async Support

The `@observe` decorator works seamlessly with `async` functions.

```python
@observe(name_override="async_task")
async def process_data(data):
    await asyncio.sleep(0.1)
    return {"status": "processed"}
```

### Renaming Parent Spans (LiveKit Integration)

When working with frameworks like LiveKit that create their own spans (e.g., `job_entrypoint`), you might want to rename the existing span instead of creating a new child span.

```python
from livekit import agents

@observe(name_override="my_agent_entrypoint", rename_parent=True)
@agents.llm.entrypoint
async def entrypoint(ctx: JobContext):
    # This will rename the span created by @agents.llm.entrypoint
    ...
```

## Global Call ID

VoiceEval SDK automatically assigns a unique **Global Call ID** to every execution context. This ID is shared across all traces generated within a single request or task, allowing you to correlate logs and traces easily.

- A new Call ID is generated automatically when the first `@observe` decorated function is called.
- Nested calls (sync or async) inherit the same Call ID.
- Separate tasks (e.g., `asyncio.create_task`) will have their own unique Call IDs unless context is manually propagated.

### Accessing the Call ID

You can access the current Call ID at runtime using `get_call_id`. This is useful for logging or returning the ID to the client.

```python
from voiceeval import get_call_id, observe

@observe()
async def handle_request(user_input):
    call_id = get_call_id()
    print(f"Processing request with Call ID: {call_id}")

    response = await generate_response(user_input)
    return {
        "response": response,
        "trace_id": call_id
    }
```

### Accessing Call Metadata

For more detailed access, use `get_call_metadata()`:

```python
from voiceeval import get_call_metadata

metadata = get_call_metadata()
if metadata:
    print(f"Current Call ID: {metadata.call_id}")
```
