# Introducing Token Trackr: Take Control of Your LLM Costs Across Multi-Cloud

**Stop guessing. Start tracking.**

---

If you're building AI-powered applications in 2024, you're probably using LLMs from multiple providers — maybe Claude on AWS Bedrock, GPT-4 on Azure OpenAI, and Gemini for specific use cases. And if you're like most teams, you have no idea how much each tenant, application, or team is actually spending on tokens.

That's why I built **Token Trackr**.

## The Problem

LLM APIs charge by the token. A single API call might cost $0.001 or $0.50 depending on the model and context length. Multiply that by thousands of requests across multiple tenants, and you've got a billing nightmare.

The challenges compound when you're running workloads across:
- **Kubernetes clusters** (EKS, AKS, GKE)
- **Virtual machines** (EC2, Azure VMs, GCE)
- **Multiple LLM providers** (AWS Bedrock, Azure OpenAI, Google Gemini)

Most teams discover their LLM costs at the end of the month — when the cloud bill arrives. By then, it's too late.

## The Solution

**Token Trackr** is an open-source, multi-tenant SaaS platform that tracks every LLM token in real-time. It calculates costs as they happen, aggregates usage by tenant, and gives you the visibility you need to control AI spending.

### How It Works

1. **Wrap your LLM calls** with our lightweight Python or Node.js SDK
2. **Tokens are captured automatically** — prompt tokens, completion tokens, latency, and metadata
3. **Costs are calculated in real-time** using configurable pricing (with tenant-specific discounts)
4. **Query usage via REST API** or visualize with pre-built Grafana dashboards

That's it. No code changes to your LLM logic. Just wrap and go.

## Key Features

### 🌐 Multi-Cloud, Multi-Provider
Track tokens from AWS Bedrock, Azure OpenAI, and Google Gemini — all in one place. The SDK auto-detects whether you're running on K8s, EC2, Azure VMs, or GCE and captures that metadata.

### 👥 Multi-Tenant by Design
Isolate usage data by tenant. Apply different pricing. Generate per-tenant billing reports. Perfect for SaaS platforms serving multiple customers.

### ⚡ Non-Blocking & Lightweight
The SDK sends events asynchronously with local queue fallback. Your LLM calls never slow down, even if Token Trackr is temporarily unavailable.

### 📊 Built-in Dashboards
Pre-configured Grafana dashboards show you:
- Tokens and cost by tenant
- Usage breakdown by model and provider
- Kubernetes vs. VM infrastructure split
- Latency percentiles

### 🚀 Deploy Anywhere
- **Kubernetes**: Full manifests with HPA, CronJobs, and Kustomize support
- **VMs**: Systemd service with install script
- **Local**: Docker Compose for development

## Who Is This For?

- **Platform teams** running AI workloads for multiple internal teams
- **SaaS companies** needing to bill customers for LLM usage
- **FinOps teams** trying to understand and control AI cloud spend
- **Developers** who want visibility into their LLM costs during development

## Quick Example

Here's how simple it is to start tracking tokens in Python:

```python
import boto3
from token_trackr import BedrockWrapper

# Your existing Bedrock client
bedrock = boto3.client("bedrock-runtime")

# Wrap it with Token Trackr
wrapper = BedrockWrapper(bedrock)

# Use it exactly like before — tokens are tracked automatically
response = wrapper.invoke_model(
    modelId="anthropic.claude-3-sonnet-20240229-v1:0",
    body=json.dumps({"messages": [{"role": "user", "content": "Hello!"}]})
)
```

That's the entire integration. Every call is now tracked, costed, and queryable.

## What's Under the Hood

- **FastAPI backend** with async PostgreSQL
- **Configurable pricing engine** with YAML-based pricing and tenant overrides
- **Aggregation jobs** that roll up raw events into daily and monthly summaries
- **Prometheus metrics** for operational monitoring
- **GitHub Actions CI/CD** with full test coverage

## Get Started

Token Trackr is open source and ready to use.

🔗 **GitHub Repository**: [https://github.com/JustInCache/token-trackr](https://github.com/JustInCache/token-trackr)

```bash
# Clone and start
git clone https://github.com/JustInCache/token-trackr.git
cd token-trackr
docker-compose up -d

# API: http://localhost:8000
# Grafana: http://localhost:3000 (admin/admin)
```

## What's Next

This is just the beginning. On the roadmap:
- Real-time budget alerts
- Cost anomaly detection
- More LLM provider integrations
- Billing system integrations

---

If you're tired of surprise LLM bills and want real visibility into your AI costs, give Token Trackr a try. Star the repo, open an issue, or contribute — I'd love to hear your feedback.

**Because in the age of AI, every token counts.**

---

*Built with ❤️ for the AI-first generation.*

🔗 **Repository**: [github.com/JustInCache/token-trackr](https://github.com/JustInCache/token-trackr)

☕ **If you find this project helpful, consider giving it a ⭐ on GitHub or [buying me a coffee](https://buymeacoffee.com) to support continued development!**

