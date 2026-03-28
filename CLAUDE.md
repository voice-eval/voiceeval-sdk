# VoiceEval SDK

OpenTelemetry-based observability SDK that customers install in their LiveKit voice agent applications. It captures traces of all calls (LLM interactions, function calls, agent logic) and exports them to VoiceEval's backend via OTLP.

## Architecture Overview

```
Customer's LiveKit Agent
  └─> voiceeval SDK (auto-instrumented LLM calls + LiveKit spans)
        └─> CallIdSpanProcessor (injects call_id, agent_name per span)
              └─> OTel BatchSpanProcessor
                    └─> PostProcessingSpanExporter (enforce_name_override)
                          └─> OTLPSpanExporter (OTLP/HTTP protobuf)
                                └─> VoiceEval Backend (/v1/traces)
                                      ├─ Validates API key (Bearer token → SHA256 hash → MongoDB lookup)
                                      ├─ Injects voiceeval.tenant.email + tenant.id into resource spans
                                      ├─ Forwards to Langfuse (OTLP protobuf, for dashboard)
                                      ├─ Creates/updates v2_calls records (has_trace=false initially)
                                      └─ On root span detection → debounced Langfuse fetch (30s):
                                           ├─ GET /api/public/traces/{traceId} from Langfuse
                                           ├─ Saves complete trace to monitoring_traces collection
                                           ├─ Sets has_trace=true on v2_calls
                                           └─ If has_audio also true → triggers auto-evaluation

Customer pushes audio separately:
  └─> POST /api/v1/monitoring/audio/{call_id}  (on voiceeval-backend)
        └─> Stores recording → sets has_audio=true
              └─> Both flags true → triggers auto-evaluation pipeline
```

## SDK Package Structure

```
src/voiceeval/
├── __init__.py                          # Public API: Client, observe, get_call_id, get_call_metadata, CallMetadata, monitor_call, skip_call
├── client.py                            # Main Client class — initializes OTel, validates API key, instruments libraries
├── context.py                           # Call ID + monitoring control via contextvars (task-local)
├── models.py                            # Pydantic models: Call, Span, Transcript
├── observability/
│   ├── instrumentation.py               # @observe decorator — creates spans, attaches call_id, inputs/outputs
│   ├── processor.py                     # CallIdSpanProcessor — auto-injects call_id/agent_name into every span
│   └── exporters.py                     # PostProcessingSpanExporter wrapping OTLPSpanExporter; enforce_name_override
├── audio/                               # Placeholder modules (ingestion, transcription, vad)
├── metrics/                             # Evaluation metric definitions (base, conversation, performance, voice)
└── runners/                             # OfflineRunner, Simulator (batch/test execution)
```

## Key Components

### Client (`client.py`)
- **Init**: Takes `api_key` (or `VOICE_EVAL_API_KEY` env var), `base_url` (default: `https://api.voiceeval.com/v1/traces`), `agent_name`, `auto_monitor`, `sample_rate`, and optional `span_post_processors`
- **Validation**: Calls `/v1/auth/validate` with Bearer token on init; raises on 403, warns on other errors
- **OTel setup**: Creates `TracerProvider` → adds `CallIdSpanProcessor` first (injects call_id) → adds `BatchSpanProcessor` with `PostProcessingSpanExporter` → `OTLPSpanExporter`
- **Auto-instrumentation**: Discovers all `opentelemetry_instrumentor` entry points (OpenAI, Anthropic, Gemini) and calls `.instrument()`. Gracefully skips uninstalled libraries with debug-level "not installed, skipping" messages.
- **LiveKit instrumentation**: Calls `livekit.agents.telemetry.set_tracer_provider()` if livekit-agents is installed
- **`flush()`**: Force-flushes the TracerProvider (OTel auto-flushes on exit via atexit handler, so flush() is only needed mid-execution)

### CallIdSpanProcessor (`observability/processor.py`)
The primary mechanism for trace linkage. Runs on every span start:
- **Root span detection**: When span name is `"job_entrypoint"` or `"job entrypoint"`, generates a fresh `call_id` UUID and stores in contextvar
- **Child spans**: Reuse the `call_id` from the current context
- **Attributes injected**: `voiceeval.call_id`, `voiceeval.agent_name`, `gen_ai.system = "voiceeval"`
- **Selective monitoring**: Respects `auto_monitor`, `sample_rate`, `monitor_call()`, and `skip_call()` settings

### Call Context (`context.py`)
- Uses `contextvars.ContextVar` for task-local storage
- `CallMetadata` dataclass with `call_id: str` (UUID)
- `ensure_call_metadata()` — creates on first call, reuses within same async task/thread
- `get_call_id()` / `get_call_metadata()` — retrieve current call ID from anywhere
- `monitor_call()` — explicitly opt a call into monitoring (for `auto_monitor=False` mode)
- `skip_call()` — opt a call out of monitoring (spans still go to Langfuse but no call_id → no MongoDB/eval)

### @observe Decorator (`observability/instrumentation.py`)
Optional manual tracing for non-LLM functions:
- Works with sync and async functions
- Every span gets: `voiceeval.call_id`, `voiceeval.inputs`, `voiceeval.output`, `gen_ai.system = "voiceeval"`
- **`name_override`**: Custom span name; also sets `voiceeval.trace_name_override` attribute
- **`rename_parent`**: Instead of creating a child span, renames the current parent span

### PostProcessingSpanExporter (`observability/exporters.py`)
- Wraps the real `OTLPSpanExporter`
- Runs a pipeline of post-processors before export
- `enforce_name_override` — forces span name to match `voiceeval.trace_name_override` attribute (uses `span._name` hack for read-only spans)

## Selective Monitoring

### Client-level options
- `auto_monitor=True` (default): Every call gets a call_id and is monitored
- `auto_monitor=False`: Only calls where `monitor_call()` is invoked are monitored
- `sample_rate=1.0` (default): Monitor 100% of calls. Set to e.g. `0.1` for 10%

### Per-call control
```python
from voiceeval import monitor_call, skip_call

# In auto_monitor=False mode, explicitly opt in:
monitor_call()

# In auto_monitor=True mode, explicitly opt out:
skip_call()
```

When a call is skipped, spans still flow to Langfuse (for the dashboard) but don't get a `voiceeval.call_id`, so they won't create MongoDB records or trigger evaluations.

## LiveKit Multi-Process Behavior

LiveKit Agents spawns an inference subprocess where module-level `Client(...)` runs again. This means:
- **Two call_ids**: Each process gets its own call_id (contextvar is per-process)
- **One trace_id**: Both processes share the same OTel trace_id
- **Backend handles this**: Debounce is keyed by trace_id. Root span (`job_entrypoint`) only appears in the main process, so only that trace_id becomes eligible for Langfuse fetch. The subprocess's call_id creates a `v2_calls` record with `has_trace=false` but never triggers a fetch.

## Span Attributes

| Attribute | Description |
|-----------|-------------|
| `voiceeval.call_id` | UUID linking all spans in one call execution context |
| `voiceeval.agent_name` | Agent name from Client init |
| `voiceeval.inputs` | Stringified function arguments (from @observe) |
| `voiceeval.output` | Stringified return value (from @observe) |
| `voiceeval.kwargs` | Stringified keyword arguments (from @observe) |
| `voiceeval.trace_name_override` | Custom span name to enforce at export time |
| `voiceeval.tenant.email` | Injected by backend from API key lookup |
| `tenant.id` | Injected by backend (same as tenant email currently) |
| `gen_ai.system` | Always `"voiceeval"` |

## API Key Flow

1. Admin creates key: `POST /v1/auth/keys` with `{"email": "client@example.com"}`
2. Server generates `secrets.token_urlsafe(32)`, stores SHA256 hash in MongoDB `sdk.api_keys` collection
3. Client receives raw key (shown once), sets as `VOICE_EVAL_API_KEY` env var
4. SDK sends key as `Authorization: Bearer <key>` on every OTLP export
5. Backend hashes incoming key, looks up in MongoDB, resolves user email + tenant_id

## End-to-End Flow: Trace + Audio → Evaluation

### SDK Customers (traces via SDK, audio pushed separately)
1. SDK captures traces → backend receives OTLP protobuf at `/v1/traces`
2. Backend forwards to Langfuse + creates `v2_calls` records + detects root span
3. After 30s debounce (reset on each new batch), fetches complete trace from Langfuse API
4. Saves trace to `monitoring_traces`, sets `has_trace=true`
5. Customer pushes audio: `POST /api/v1/monitoring/audio/{call_id}` → `has_audio=true`
6. Both flags true → `trigger_monitoring_evaluation()`:
   - Download audio → transcribe via Sarvam STT → run evaluation engine → save results
   - Call status: `call_done → transcribing → evaluating → evals_done`

### Non-SDK Customers (traces + audio in one push)
1. Customer sends `POST /api/v1/monitoring/ingest` with `call_id`, `audio_url`, `traces[]`
2. Backend stores recording + traces → both `has_trace` and `has_audio` set true immediately
3. Evaluation triggers immediately (same pipeline)

## Customer Setup

```python
# Install
pip install voiceeval-sdk

# In their LiveKit agent code — just initialize the Client at module level
from voiceeval import Client

client = Client(
    api_key="ve_xxxxx",             # or set VOICE_EVAL_API_KEY env var
    agent_name="my-booking-agent",  # identifies this agent in the dashboard
    # auto_monitor=True,            # default: monitor all calls
    # sample_rate=1.0,              # default: 100% of calls
)

# That's it! All LLM calls and LiveKit spans are automatically traced.
# No @observe decorator or client.flush() required — OTel flushes on exit.
```

## Development

```bash
# Install dependencies
uv sync

# Run tests
pytest

# Build package
hatch build
```

## Version
Current: 0.1.9 (Python 3.10+, Hatchling build)
