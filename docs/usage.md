# Usage Guide

This guide provides instructions on how to install, configure, and use the VoiceEval SDK for Python.

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
    api_key="your_api_key_here",
    base_url="https://api.voiceeval.com/v1/traces"
)
```

You can also provide configuration via environment variables:

- `VOICE_EVAL_API_KEY`: Your API key.
- `VOICE_EVAL_BASE_URL`: The URL for the trace collector (default: `https://api.voiceeval.com/v1/traces`).

If environment variables are set, you can initialize the client without arguments:

```python
client = Client()
```

## Auto-Instrumentation

The SDK automatically instruments the following libraries if they are installed in your environment:

- OpenAI (`openai`)
- Anthropic (`anthropic`)
- Google Gemini (`google-generativeai`)

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

## Manual Tracing

For functions that do not directly call LLMs but contain important logic (such as RAG retrieval or preprocessing), you can use the `@observe` decorator.

```python
from voiceeval import observe

@observe(name_override="document_retrieval")
def retrieve_documents(query: str):
    # Logic to retrieve documents
    return ["doc1", "doc2"]
```

## Configuration

The `Client` accepts the following optional arguments:

- `api_key` (str): Authentication key for the VoiceEval service.
- `base_url` (str): Endpoint URL for trace ingestion.
- `project_name` (str): Optional project identifier for grouping traces.
