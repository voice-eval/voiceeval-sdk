# VoiceEval SDK (Python)

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)
[![OpenTelemetry](https://img.shields.io/badge/OpenTelemetry-Native-purple)](https://opentelemetry.io/)

**VoiceEval** is an enterprise-grade observability and evaluation SDK for Voice Agents and LLM-powered applications. Built on OpenTelemetry, it provides zero-config auto-instrumentation with detailed tracing, latency breakdown, and cost analysis.

## Key Features

- **Zero-Config Auto-Instrumentation**: Automatically traces calls from major LLM providers (OpenAI, Anthropic, Google Gemini) and LiveKit Agents — no code changes needed.
- **LiveKit Native**: Automatically integrates with LiveKit's tracing infrastructure. Just initialize the Client and all agent spans are captured.
- **Selective Monitoring**: Control which calls are traced with `auto_monitor`, `sample_rate`, `monitor_call()`, and `skip_call()`.
- **High Performance**: Built on OpenTelemetry with async batch exports (OTLP/HTTP), ensuring negligible runtime overhead.

## Installation

```bash
pip install voiceeval-sdk
# or
uv add voiceeval-sdk
```

## Quickstart

### 1. Initialize the Client

Add a single `Client(...)` call at the top of your agent file. This sets up OTel tracing and auto-instruments all installed LLM libraries and LiveKit.

```python
from voiceeval import Client

client = Client(
    api_key="your_voiceeval_api_key",   # or set VOICE_EVAL_API_KEY env var
    agent_name="my-booking-agent",      # identifies this agent in the dashboard
)
```

That's it. No `@observe` decorator, no `client.flush()` — OTel flushes automatically on process exit.

### 2. LiveKit Agent Example

```python
from livekit.agents import Agent, AgentSession, JobContext, cli
from voiceeval import Client

# Initialize VoiceEval — auto-instruments all LLM calls and LiveKit spans
client = Client(
    api_key="your_voiceeval_api_key",
    agent_name="my-booking-agent",
)

class MyAgent(Agent):
    def __init__(self):
        super().__init__(instructions="You are a helpful voice assistant.")

@server.rtc_session(agent_name="my-agent")
async def entrypoint(ctx: JobContext):
    session = AgentSession(
        stt=...,
        llm=...,
        tts=...,
    )
    await session.start(agent=MyAgent(), room=ctx.room)
    await ctx.connect()
```

### 3. Standalone LLM Example

Works without LiveKit too — any OpenAI/Anthropic/Gemini calls are automatically traced:

```python
from voiceeval import Client
from openai import OpenAI

client = Client(api_key="your_voiceeval_api_key")

openai_client = OpenAI()
response = openai_client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "Hello world"}]
)
# Trace is automatically captured and exported
```

## Client Options

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `api_key` | `str` | `VOICE_EVAL_API_KEY` env var | Your VoiceEval API key |
| `base_url` | `str` | `https://api.voiceeval.com/v1/traces` | VoiceEval ingestion endpoint |
| `agent_name` | `str` | `None` | Agent identifier shown in the dashboard |
| `auto_monitor` | `bool` | `True` | Monitor all calls automatically |
| `sample_rate` | `float` | `1.0` | Fraction of calls to monitor (0.0 to 1.0) |
| `span_post_processors` | `list` | `None` | Custom span post-processing functions |

## Selective Monitoring

By default, every call is monitored (`auto_monitor=True`). You can control this at the client level or per-call.

### Sample a fraction of calls

```python
client = Client(
    api_key="your_key",
    sample_rate=0.1,  # Randomly monitor 10% of calls
)
```

### Skip specific calls (`auto_monitor=True`)

With the default `auto_monitor=True`, all calls are monitored. Use `skip_call()` inside your session handler to opt out a specific call:

```python
from voiceeval import Client, skip_call

client = Client(api_key="your_key")  # auto_monitor=True by default

@server.rtc_session(agent_name="my-agent")
async def entrypoint(ctx: JobContext):
    # Decide based on room metadata, participant info, etc.
    if ctx.room.name.startswith("internal-"):
        skip_call()  # This call won't be monitored or evaluated

    session = AgentSession(stt=..., llm=..., tts=...)
    await session.start(agent=MyAgent(), room=ctx.room)
    await ctx.connect()
```

### Monitor specific calls (`auto_monitor=False`)

With `auto_monitor=False`, no calls are monitored unless you explicitly opt in with `monitor_call()`:

```python
from voiceeval import Client, monitor_call

client = Client(
    api_key="your_key",
    auto_monitor=False,  # Nothing monitored by default
)

@server.rtc_session(agent_name="my-agent")
async def entrypoint(ctx: JobContext):
    # Only monitor production calls, not test rooms
    if not ctx.room.name.startswith("test-"):
        monitor_call()  # This call will be traced and evaluated

    session = AgentSession(stt=..., llm=..., tts=...)
    await session.start(agent=MyAgent(), room=ctx.room)
    await ctx.connect()
```

When a call is skipped (or not opted in), spans still flow to Langfuse for the dashboard but won't create backend records or trigger evaluations.

## Manual Tracing (Optional)

For non-LLM functions like business logic or RAG pipelines, use the `@observe` decorator:

```python
from voiceeval import observe

@observe(name_override="rag_retrieval")
def retrieve_documents(query: str):
    # Your logic here
    return docs
```

## License

MIT
