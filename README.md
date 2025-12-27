# VoiceEval SDK (Python)

[![Python](https://img.shields.io/badge/Python-3.11%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)
[![OpenTelemetry](https://img.shields.io/badge/OpenTelemetry-Native-purple)](https://opentelemetry.io/)

**VoiceEval** is an enterprise-grade observability and evaluation SDK designed specifically for Voice Agents and LLM-powered applications. It provides detailed tracing, latency breakdown, and cost analysis with zero configuration.

## 🚀 Key Features

- **🔎 Zero-Config Auto-Instrumentation**: Automatically detects and traces calls from major LLM providers (OpenAI, Anthropic, Google Gemini) without any code changes.
- **🛡️ Secure Ingestion Proxy**: All traces are sent through a secure proxy (`server/`), separating your application logic from downstream observability backends (like Langfuse). This ensures you maintain full control over your data and API keys.
- **⚡ High Performance**: Built on top of `OpenTelemetry`, utilizing efficient asynchronous Batch exports (`OTLP/HTTP`) to ensure negligible runtime overhead.
- **🧩 Standardized Data Model**: Uses standard OTel semantic conventions, making your data portable and interoperable with any OTel-compatible backend.

## 📦 Installation

Install the SDK via `pip` (or `uv`):

```bash
pip install voiceeval-sdk
# or
uv add voiceeval-sdk
```

For local development:
```bash
git clone https://github.com/voiceeval/voiceeval-sdk.git
cd voiceeval-sdk
pip install -e .
```

## 🏁 Quickstart

### 1. Initialize the Client

Initialize the `Client` at the start of your application. This single line sets up the OTel exporter and enables auto-instrumentation for all installed LLM libraries.

```python
from voiceeval import Client

# Initialize SDK - connects to your local proxy or prod endpoint
client = Client(
    api_key="your_voiceeval_api_key",  # or set VOICE_EVAL_API_KEY env var
    base_url="http://api.voiceeval.com/v1/traces"
)
```

### 2. Run Your Agent

That's it! Any calls to supported libraries like `openai` or `anthropic` are now automatically traced.

```python
from openai import OpenAI

# No manual wrapping needed!
client_openai = OpenAI()
response = client_openai.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "Hello world"}]
)
```

### 3. Manual Tracing (Optional)

For functions that don't call LLMs (like your business logic or RAG pipeline), use the `@observe` decorator:

```python
from voiceeval import observe

@observe(name_override="rag_retrieval")
def retrieve_documents(query: str):
    # Your complex logic here
    return docs
```

## 🔌 Supported Providers

The SDK automatically instruments the following libraries if they are found in your environment:

| Provider | Library | Status |
| :--- | :--- | :--- |
| **OpenAI** | `openai` | ✅ Auto-Instrumented |
| **Anthropic** | `anthropic` | ✅ Auto-Instrumented |
| **Google Gemini** | `google-generativeai` | ✅ Auto-Instrumented |

*Note: If a library is not installed, the SDK gracefully skips it.*

## 📄 License

MIT
