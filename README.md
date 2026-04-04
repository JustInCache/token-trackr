# Token Trackr

A multi-tenant SaaS platform for tracking LLM token consumption across **AWS Bedrock**, **Azure OpenAI**, and **Google Gemini**. Designed to run on Kubernetes, EC2, Azure VMs, GCP Compute Engine, and bare-metal Linux.

## Features

- **Multi-Cloud Support**: Track tokens from AWS Bedrock, Azure OpenAI, and Google Gemini
- **Multi-Tenant**: Isolate usage data by tenant with configurable pricing
- **Lightweight SDKs**: Python and Node.js SDKs with async, non-blocking event sending
- **Auto Cost Calculation**: Real-time cost calculation using configurable pricing
- **Host Metadata Detection**: Automatically detect cloud provider, instance ID, and Kubernetes metadata
- **Aggregation Jobs**: Daily and monthly usage rollups for fast reporting
- **Grafana Dashboards**: Pre-built dashboards for usage visualization
- **Flexible Deployment**: Kubernetes, VM (systemd), or Docker Compose

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Application   │     │   Application   │     │   Application   │
│   (K8s Pod)     │     │   (EC2/Azure)   │     │   (GCE VM)      │
└────────┬────────┘     └────────┬────────┘     └────────┬────────┘
         │                       │                       │
         │    ┌──────────────────┴───────────────────┐   │
         └────►          Token Trackr SDK          ◄───┘
              │   (Python / Node.js)                 │
              └──────────────────┬───────────────────┘
                                 │ POST /usage
                                 ▼
              ┌──────────────────────────────────────┐
              │       Token Trackr Backend         │
              │   ┌────────────────────────────┐     │
              │   │     Cost Calculation       │     │
              │   │   (bedrock/azure/gemini)   │     │
              │   └────────────────────────────┘     │
              └──────────────────┬───────────────────┘
                                 │
              ┌──────────────────┴───────────────────┐
              │             PostgreSQL               │
              │  ┌─────────────────────────────────┐ │
              │  │ token_usage_raw                 │ │
              │  │ tenant_daily_summary            │ │
              │  │ tenant_monthly_summary          │ │
              │  │ pricing_table                   │ │
              │  └─────────────────────────────────┘ │
              └──────────────────────────────────────┘
```

## Quick Start

### 1. Start with Docker Compose

```bash
# Clone the repository
cd token-analyser

# Start services
docker-compose up -d

# Services running:
# - API: http://localhost:8000
# - Grafana: http://localhost:3000 (admin/admin)
# - PostgreSQL: localhost:5432
# - Redis: localhost:6379
```

### 2. Install the SDK

**Python:**
```bash
pip install token-trackr-sdk[all]
```

**Node.js:**
```bash
npm install token-trackr-sdk
```

### 3. Track Token Usage

**Python (AWS Bedrock):**
```python
import boto3
from token_trackr import BedrockWrapper

bedrock = boto3.client("bedrock-runtime")
wrapper = BedrockWrapper(bedrock)

response = wrapper.invoke_model(
    modelId="anthropic.claude-3-sonnet-20240229-v1:0",
    body=json.dumps({
        "messages": [{"role": "user", "content": "Hello!"}],
        "max_tokens": 100,
    }),
)
# Tokens automatically tracked!
```

**Node.js (Azure OpenAI):**
```typescript
import { OpenAIClient, AzureKeyCredential } from "@azure/openai";
import { AzureOpenAIWrapper } from "token-trackr-sdk";

const client = new OpenAIClient(endpoint, new AzureKeyCredential(key));
const wrapper = new AzureOpenAIWrapper(client);

const response = await wrapper.getChatCompletions("gpt-4o", [
  { role: "user", content: "Hello!" },
]);
// Tokens automatically tracked!
```

### 4. Query Usage

```bash
# Get tenant summary
curl http://localhost:8000/tenant/my-tenant/summary

# Get daily usage
curl http://localhost:8000/tenant/my-tenant/daily

# Get available models/pricing
curl http://localhost:8000/provider/bedrock/models
```

## Project Structure

```
token-analyser/
├── backend/                    # FastAPI backend
│   ├── api/                    # REST API endpoints
│   ├── core/                   # Cost calculation engine
│   ├── jobs/                   # Aggregation jobs & scheduler
│   ├── models/                 # SQLAlchemy ORM models
│   ├── schemas/                # Pydantic schemas
│   ├── services/               # Business logic
│   └── main.py                 # Application entry point
├── sdk/
│   ├── python/                 # Python SDK
│   │   └── src/token_trackr/
│   │       └── wrappers/       # Bedrock, Azure, Gemini wrappers
│   └── nodejs/                 # Node.js SDK
│       └── src/
│           └── wrappers/       # Bedrock, Azure, Gemini wrappers
├── config/
│   └── pricing.yaml            # Token pricing configuration
├── database/
│   └── init.sql                # Database initialization
├── alembic/                    # Database migrations
├── grafana/                    # Dashboard provisioning
│   ├── dashboards/             # JSON dashboard files
│   └── provisioning/           # Datasource & dashboard config
├── deploy/
│   ├── kubernetes/             # K8s manifests
│   │   ├── deployment.yaml
│   │   ├── service.yaml
│   │   ├── hpa.yaml
│   │   ├── cronjob.yaml
│   │   └── kustomization.yaml
│   └── vm/                     # VM deployment
│       ├── install.sh
│       ├── token-trackr-api.service
│       └── token-trackr.env
├── docker-compose.yml
├── Dockerfile
└── pyproject.toml
```

## API Reference

### POST /usage

Record a token usage event.

```json
{
  "tenant_id": "my-tenant",
  "provider": "bedrock",
  "model": "anthropic.claude-3-sonnet-20240229-v1:0",
  "prompt_tokens": 150,
  "completion_tokens": 50,
  "timestamp": "2024-12-20T10:30:00Z",
  "latency_ms": 1500,
  "host": {
    "hostname": "app-server-1",
    "cloud_provider": "aws",
    "instance_id": "i-1234567890abcdef",
    "k8s": {
      "pod": "app-abc123",
      "namespace": "production"
    }
  }
}
```

### GET /tenant/{tenant_id}/summary

Get overall usage summary.

```json
{
  "tenant_id": "my-tenant",
  "total_requests": 15000,
  "total_prompt_tokens": 2500000,
  "total_completion_tokens": 500000,
  "total_tokens": 3000000,
  "total_cost": 45.50,
  "by_provider": { ... },
  "by_model": { ... },
  "by_cloud_provider": { ... }
}
```

### GET /tenant/{tenant_id}/daily

Get daily usage with optional date range.

### GET /provider/{provider}/models

Get available models and pricing for a provider.

## Deployment

### Kubernetes

```bash
# Apply all manifests
kubectl apply -k deploy/kubernetes/

# Or apply individually
kubectl apply -f deploy/kubernetes/namespace.yaml
kubectl apply -f deploy/kubernetes/configmap.yaml
kubectl apply -f deploy/kubernetes/secret.yaml
kubectl apply -f deploy/kubernetes/deployment.yaml
kubectl apply -f deploy/kubernetes/service.yaml
kubectl apply -f deploy/kubernetes/hpa.yaml
```

### VM (EC2, Azure VM, GCE)

```bash
# Run the install script
sudo ./deploy/vm/install.sh

# Configure
sudo nano /etc/token-trackr/token-trackr.env

# Start service
sudo systemctl start token-trackr-api
sudo systemctl status token-trackr-api

# View logs
sudo journalctl -u token-trackr-api -f
```

### Docker Compose

```bash
docker-compose up -d
```

## Configuration

### Pricing Configuration

Edit `config/pricing.yaml` to configure token pricing:

```yaml
bedrock:
  anthropic.claude-3-sonnet-20240229-v1:0:
    input_per_1k: 0.003
    output_per_1k: 0.015

azure_openai:
  gpt-4o:
    input_per_1k: 0.005
    output_per_1k: 0.015

gemini:
  gemini-1.5-pro:
    input_per_1k: 0.00125
    output_per_1k: 0.005

# Tenant-specific overrides
tenant_overrides:
  enterprise-tenant:
    discount_percent: 20
```

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | Required |
| `REDIS_URL` | Redis connection string | Optional |
| `APP_SECRET_KEY` | Application secret key | Required in production |
| `LOG_LEVEL` | Logging level | `INFO` |
| `SCHEDULER_ENABLED` | Enable aggregation scheduler | `false` |

## SDK Configuration

### Python

```python
from token_trackr import TokenTrackrConfig, TokenTrackrClient

config = TokenTrackrConfig(
    backend_url="http://token-trackr:8000",
    api_key="your-api-key",
    tenant_id="my-tenant",
    batch_size=10,
    flush_interval=5.0,
    async_mode=True,
)

client = TokenTrackrClient(config)
```

### Node.js

```typescript
import { TokenTrackrConfig, TokenTrackrClient } from "token-trackr-sdk";

const config = new TokenTrackrConfig({
  backendUrl: "http://token-trackr:8000",
  apiKey: "your-api-key",
  tenantId: "my-tenant",
  batchSize: 10,
  flushInterval: 5,
  asyncMode: true,
});

const client = new TokenTrackrClient(config);
```

## Grafana Dashboards

Access Grafana at `http://localhost:3000` (default: admin/admin).

**Available Dashboards:**

1. **Token Usage Overview**: High-level metrics, usage by provider/tenant, infrastructure split
2. **Tenant Details**: Deep-dive into specific tenant usage, model breakdown, latency

## Database Migrations

```bash
# Run migrations
alembic upgrade head

# Create a new migration
alembic revision --autogenerate -m "Description"

# Downgrade
alembic downgrade -1
```

## Development

```bash
# Install dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run linting
ruff check .
black --check .

# Start development server
uvicorn backend.main:app --reload
```

## Aggregation Jobs

Jobs run automatically via:
- **Kubernetes**: CronJobs
- **VM**: Systemd timers
- **Docker**: APScheduler in worker container

| Job | Schedule | Description |
|-----|----------|-------------|
| Daily Aggregation | 2:00 AM | Roll up raw events to daily summaries |
| Monthly Aggregation | 1st of month, 3:00 AM | Roll up daily to monthly summaries |
| Billing Reports | 2nd of month, 4:00 AM | Generate CSV billing reports |

## Support the Project

If this repo saved you time or sparked an idea, consider buying me a coffee.

<a href="https://buymeacoffee.com/connectankush">
  <img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" alt="Buy Me a Coffee" width="200">
</a>

[https://buymeacoffee.com/connectankush](https://buymeacoffee.com/connectankush)

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes and add tests
4. Submit a pull request

## License

MIT License - see [LICENSE](LICENSE) for details.

