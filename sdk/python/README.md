# Token Trackr Python SDK

Python SDK for tracking LLM token consumption across AWS Bedrock, Azure OpenAI, and Google Gemini.

## Installation

```bash
# Base installation
pip install token-trackr-sdk

# With specific provider support
pip install token-trackr-sdk[bedrock]   # AWS Bedrock
pip install token-trackr-sdk[azure]     # Azure OpenAI
pip install token-trackr-sdk[gemini]    # Google Gemini
pip install token-trackr-sdk[all]       # All providers
```

## Quick Start

### Configuration

Set environment variables:

```bash
export TOKEN_TRACKR_URL="http://your-backend:8000"
export TOKEN_TRACKR_API_KEY="your-api-key"
export TOKEN_TRACKR_TENANT_ID="your-tenant-id"
```

Or configure programmatically:

```python
from token_trackr import TokenTrackrClient, TokenTrackrConfig

config = TokenTrackrConfig(
    backend_url="http://your-backend:8000",
    api_key="your-api-key",
    tenant_id="your-tenant-id",
)

client = TokenTrackrClient(config)
```

### AWS Bedrock

```python
import boto3
from token_trackr import BedrockWrapper

# Create Bedrock client
bedrock = boto3.client("bedrock-runtime")

# Wrap with token tracking
wrapper = BedrockWrapper(bedrock)

# Use as normal - tokens are automatically tracked
response = wrapper.invoke_model(
    modelId="anthropic.claude-3-sonnet-20240229-v1:0",
    body=json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "messages": [{"role": "user", "content": "Hello!"}],
        "max_tokens": 100,
    }),
)
```

### Azure OpenAI

```python
from openai import AzureOpenAI
from token_trackr import AzureOpenAIWrapper

# Create Azure OpenAI client
azure_client = AzureOpenAI(
    api_key="your-key",
    api_version="2024-02-01",
    azure_endpoint="https://your-resource.openai.azure.com",
)

# Wrap with token tracking
wrapper = AzureOpenAIWrapper(azure_client)

# Use as normal - tokens are automatically tracked
response = wrapper.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "Hello!"}],
)
```

### Google Gemini

```python
import google.generativeai as genai
from token_trackr import GeminiWrapper

# Configure Gemini
genai.configure(api_key="your-key")
model = genai.GenerativeModel("gemini-1.5-pro")

# Wrap with token tracking
wrapper = GeminiWrapper(model)

# Use as normal - tokens are automatically tracked
response = wrapper.generate_content("Hello!")
```

## Manual Recording

You can also record usage manually:

```python
from token_trackr import TokenTrackrClient

client = TokenTrackrClient()

# Record a usage event
client.record(
    provider="bedrock",
    model="anthropic.claude-3-sonnet",
    prompt_tokens=100,
    completion_tokens=50,
    latency_ms=1500,
)

# Flush to ensure all events are sent
client.flush()
```

## Features

### Automatic Host Metadata

The SDK automatically detects and includes:

- **Hostname**: Local machine hostname
- **Cloud Provider**: AWS, Azure, GCP, or on-prem
- **Instance ID**: EC2 instance ID, Azure VM ID, or GCE instance ID
- **Kubernetes**: Pod name, namespace, and node (if running in K8s)

### Non-Blocking Async Sending

Events are queued and sent in the background:

```python
config = TokenTrackrConfig(
    async_mode=True,          # Enable async mode (default)
    batch_size=10,            # Send after 10 events
    flush_interval=5.0,       # Or every 5 seconds
    max_queue_size=1000,      # Maximum events to queue
)
```

### Retry with Fallback

Failed requests are retried with exponential backoff. If all retries fail, events are saved to a local file for later recovery:

```
~/.token-trackr/fallback/events_<timestamp>.json
```

### Streaming Support

All wrappers support streaming responses with automatic token tracking after the stream completes.

## API Reference

### TokenTrackrConfig

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `backend_url` | str | `$TOKEN_TRACKR_URL` | Backend API URL |
| `api_key` | str | `$TOKEN_TRACKR_API_KEY` | API key for auth |
| `tenant_id` | str | `$TOKEN_TRACKR_TENANT_ID` | Tenant identifier |
| `batch_size` | int | 10 | Events per batch |
| `flush_interval` | float | 5.0 | Seconds between flushes |
| `max_queue_size` | int | 1000 | Max queued events |
| `retry_attempts` | int | 3 | Retry attempts |
| `timeout` | float | 30.0 | Request timeout |
| `async_mode` | bool | True | Enable async sending |

### TokenTrackrClient

| Method | Description |
|--------|-------------|
| `record(...)` | Record a usage event |
| `flush()` | Flush queued events |
| `close()` | Close client and flush |

### Provider Wrappers

| Wrapper | Provider | Methods |
|---------|----------|---------|
| `BedrockWrapper` | AWS Bedrock | `invoke_model`, `invoke_model_with_response_stream` |
| `AzureOpenAIWrapper` | Azure OpenAI | `chat.completions.create`, `completions.create`, `embeddings.create` |
| `GeminiWrapper` | Google Gemini | `generate_content`, `start_chat` |

## License

MIT

