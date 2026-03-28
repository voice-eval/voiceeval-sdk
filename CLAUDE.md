# VoiceEval SDK

OpenTelemetry-based observability SDK that customers install in their LiveKit voice agent applications. It captures traces of all calls (LLM interactions, function calls, agent logic) and exports them to VoiceEval's ingestion proxy.

## Architecture Overview

```
Customer's LiveKit Agent
  └─> voiceeval SDK (@observe decorator + auto-instrumented LLM calls)
        └─> OTel BatchSpanProcessor
              └─> PostProcessingSpanExporter (enforce_name_override)
                    └─> OTLPSpanExporter (OTLP/HTTP protobuf)
                          └─> VoiceEval Ingestion Proxy (server/main.py)
                                ├─ Validates API key (Bearer token → SHA256 hash → MongoDB lookup)
                                ├─ Injects voiceeval.tenant.email + tenant.id into resource spans
                                ├─ Forwards to Langfuse (for dashboard)
                                └─ [DUAL-WRITE] Writes directly to backend MongoDB:
                                     ├─ Extracts voiceeval.call_id from span attributes
                                     ├─ Upserts v2_calls with has_trace=true
                                     ├─ Saves spans to monitoring_traces collection
                                     └─ Checks if has_audio is also true (eval triggers in backend)

Customer pushes audio separately:
  └─> POST /api/v1/monitoring/audio/{call_id}  (on voiceeval-backend)
        └─> Stores recording → sets has_audio=true
              └─> Both flags true → triggers auto-evaluation pipeline
```

## SDK Package Structure

```
src/voiceeval/
├── __init__.py                          # Public API: Client, observe, get_call_id, get_call_metadata, CallMetadata
├── client.py                            # Main Client class — initializes OTel, validates API key, instruments libraries
├── context.py                           # Call ID management via contextvars (task-local UUID shared across nested calls)
├── models.py                            # Pydantic models: Call, Span, Transcript
├── observability/
│   ├── instrumentation.py               # @observe decorator — creates spans, attaches call_id, inputs/outputs
│   └── exporters.py                     # PostProcessingSpanExporter wrapping OTLPSpanExporter; enforce_name_override
├── audio/                               # Placeholder modules (ingestion, transcription, vad)
├── metrics/                             # Evaluation metric definitions (base, conversation, performance, voice)
└── runners/                             # OfflineRunner, Simulator (batch/test execution)

server/                                  # Ingestion proxy (separate FastAPI app, runs on port 8001)
├── main.py                              # /v1/traces (ingest + dual-write), /v1/auth/validate, /v1/auth/keys
├── services.py                          # AuthService — API key generation (secrets.token_urlsafe), SHA256 hashing, MongoDB lookup
├── database.py                          # MongoDB connection (Motor) — sdk DB + backend tenant DBs
├── models.py                            # User, APIKey Pydantic models
└── utils.py                             # CLI utilities
```

## Key Components

### Client (`client.py`)
- **Init**: Takes `api_key` (or `VOICE_EVAL_API_KEY` env var) and `base_url` (default: `https://api.voiceeval.com/v1/traces`)
- **Validation**: Calls `/v1/auth/validate` with Bearer token on init; raises on 403, warns on other errors
- **OTel setup**: Creates `TracerProvider` → `OTLPSpanExporter` (with Bearer auth header) → `BatchSpanProcessor`
- **Auto-instrumentation**: Discovers all `opentelemetry_instrumentor` entry points (OpenAI, Anthropic, Gemini) and calls `.instrument()`
- **LiveKit instrumentation**: Calls `livekit.agents.telemetry.set_tracer_provider()` if livekit-agents is installed
- **`flush()`**: Force-flushes the TracerProvider before shutdown

### @observe Decorator (`observability/instrumentation.py`)
- Works with sync and async functions
- First `@observe` call in an execution context creates a `CallMetadata` (UUID) via `ensure_call_metadata()`
- Every span gets: `voiceeval.call_id`, `voiceeval.inputs`, `voiceeval.output`, `gen_ai.system = "voiceeval"`
- **`name_override`**: Custom span name; also sets `voiceeval.trace_name_override` attribute
- **`rename_parent`**: Instead of creating a child span, renames the current parent span (useful for LiveKit's `job_entrypoint` spans)
- **Auto-detect**: If current parent span is named `"job entrypoint"` or `"job_entrypoint"`, automatically renames it

### Call ID Context (`context.py`)
- Uses `contextvars.ContextVar` for task-local storage
- `CallMetadata` dataclass with `call_id: str` (UUID)
- `ensure_call_metadata()` — creates on first call, reuses within same async task/thread
- `get_call_id()` / `get_call_metadata()` — retrieve current call ID from anywhere in the call chain

### PostProcessingSpanExporter (`observability/exporters.py`)
- Wraps the real `OTLPSpanExporter`
- Runs a pipeline of post-processors before export
- `enforce_name_override` — forces span name to match `voiceeval.trace_name_override` attribute (uses `span._name` hack for read-only spans)

### Ingestion Proxy (`server/main.py`)
- **POST `/v1/traces`**: Receives OTLP protobuf, parses it, injects `voiceeval.tenant.email` and `tenant.id` into resource attributes, forwards to Langfuse, **AND dual-writes to backend MongoDB**
- **GET `/v1/auth/validate`**: Validates Bearer token against hashed keys in MongoDB
- **POST `/v1/auth/keys`**: Creates new API key for a user email
- Falls back to forwarding original body if protobuf parsing fails (logged as error)

### Dual-Write to Backend MongoDB (`server/main.py`)
When `/v1/traces` receives spans:
1. `_extract_call_ids_and_spans()` parses `voiceeval.call_id` from span attributes and serializes span data
2. `_dual_write_to_backend()` runs as a non-blocking `asyncio.create_task()`:
   - For each `call_id` found in spans:
     - Upserts `v2_calls` record with `has_trace=true`, `source="monitoring"`, `sdk_call_id=call_id`
     - Saves/updates `monitoring_traces` document with span data and aggregated metrics (tokens, cost, LLM calls, errors)
     - Checks if `has_audio` is also true (eval triggered by backend when both flags are set)
3. Tenant resolution: uses `config.tenant_id` from the API key's config (defaults to `"default"`)

### Database (`server/database.py`)
- `Database.get_db()` → `sdk` database (api_keys, users collections)
- `Database.get_backend_db(tenant_id)` → `voiceeval` or `voiceeval_{tenant_id}` (backend's tenant DB)
- `Database.get_v2_calls_collection(tenant_id)` → `v2_calls` collection in backend DB
- `Database.get_monitoring_traces_collection(tenant_id)` → `monitoring_traces` collection in backend DB

## Span Attributes

| Attribute | Description |
|-----------|-------------|
| `voiceeval.call_id` | UUID linking all spans in one call execution context |
| `voiceeval.inputs` | Stringified function arguments |
| `voiceeval.output` | Stringified return value |
| `voiceeval.kwargs` | Stringified keyword arguments |
| `voiceeval.trace_name_override` | Custom span name to enforce at export time |
| `voiceeval.tenant.email` | Injected by proxy from API key lookup |
| `tenant.id` | Injected by proxy (same as tenant email currently) |
| `gen_ai.system` | Always `"voiceeval"` |

## API Key Flow

1. Admin creates key: `POST /v1/auth/keys` with `{"email": "client@example.com"}`
2. Server generates `secrets.token_urlsafe(32)`, stores SHA256 hash in MongoDB `api_keys` collection linked to user
3. Client receives raw key (shown once), sets as `VOICE_EVAL_API_KEY` env var
4. SDK sends key as `Authorization: Bearer <key>` on every OTLP export
5. Proxy hashes incoming key, looks up in MongoDB, resolves user email, injects into spans
6. Proxy dual-writes traces directly to backend MongoDB (tenant resolved from `config.tenant_id` on API key)

## End-to-End Trace + Audio → Evaluation Flow

### SDK Customers (traces via SDK, audio pushed separately)
1. SDK captures traces → proxy receives OTLP protobuf
2. Proxy dual-writes: forward to Langfuse + write to `monitoring_traces` + upsert `v2_calls` with `has_trace=true`
3. Customer pushes audio: `POST /api/v1/monitoring/audio/{call_id}` → recording saved → `has_audio=true`
4. Both flags true → backend triggers `trigger_monitoring_evaluation()`:
   - Download audio → transcribe via Sarvam STT → run evaluation engine → save results
   - Call status: `call_done → transcribing → evaluating → evals_done`

### Non-SDK Customers (traces + audio in one push)
1. Customer sends `POST /api/v1/monitoring/ingest` with `call_id`, `audio_url`, `traces[]`
2. Backend stores recording + traces → both `has_trace` and `has_audio` set true immediately
3. Evaluation triggers immediately (same pipeline as above)

### Simulation Calls (existing flow, unchanged)
1. Backend creates call with `test_case_id` → LiveKit simulation runs → recording saved
2. `evaluate_v2_call()` runs transcription + evaluation (separate code path, not monitoring pipeline)
3. If SDK is installed on the agent: traces arrive via proxy dual-write, linked via `sdk_call_id`

## Customer Setup

```python
# Install
pip install voiceeval-sdk

# In their LiveKit agent code
from voiceeval import Client, observe, get_call_id

client = Client(api_key="ve_xxxxx")  # or set VOICE_EVAL_API_KEY env var

@observe(name_override="my-voice-agent", rename_parent=True)
async def entrypoint(ctx: JobContext):
    # All OpenAI/Anthropic/Gemini calls are auto-traced
    # Call ID available via get_call_id()
    ...

client.flush()  # Before shutdown
```

## Development

```bash
# Install dependencies
uv sync

# Run tests
pytest

# Run ingestion proxy locally
python -m server.main  # Starts on port 8001

# Build package
hatch build
```

## Version
Current: 0.1.6 (Python 3.11+, Hatchling build)
