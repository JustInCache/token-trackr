# Token Trackr Node.js SDK

Node.js SDK for tracking LLM token consumption across AWS Bedrock, Azure OpenAI, and Google Gemini.

## Installation

```bash
npm install token-trackr-sdk

# With specific provider support
npm install token-trackr-sdk @aws-sdk/client-bedrock-runtime
npm install token-trackr-sdk @azure/openai
npm install token-trackr-sdk @google/generative-ai
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

```typescript
import { TokenTrackrClient, TokenTrackrConfig } from "token-trackr-sdk";

const config = new TokenTrackrConfig({
  backendUrl: "http://your-backend:8000",
  apiKey: "your-api-key",
  tenantId: "your-tenant-id",
});

const client = new TokenTrackrClient(config);
```

### AWS Bedrock

```typescript
import { BedrockRuntimeClient } from "@aws-sdk/client-bedrock-runtime";
import { BedrockWrapper } from "token-trackr-sdk";

const bedrock = new BedrockRuntimeClient({ region: "us-east-1" });
const wrapper = new BedrockWrapper(bedrock);

const response = await wrapper.invokeModel({
  modelId: "anthropic.claude-3-sonnet-20240229-v1:0",
  body: JSON.stringify({
    anthropic_version: "bedrock-2023-05-31",
    messages: [{ role: "user", content: "Hello!" }],
    max_tokens: 100,
  }),
});
```

### Azure OpenAI

```typescript
import { OpenAIClient, AzureKeyCredential } from "@azure/openai";
import { AzureOpenAIWrapper } from "token-trackr-sdk";

const azureClient = new OpenAIClient(
  "https://your-resource.openai.azure.com",
  new AzureKeyCredential("your-key")
);
const wrapper = new AzureOpenAIWrapper(azureClient);

const response = await wrapper.getChatCompletions("gpt-4o", [
  { role: "user", content: "Hello!" },
]);
```

### Google Gemini

```typescript
import { GoogleGenerativeAI } from "@google/generative-ai";
import { GeminiWrapper } from "token-trackr-sdk";

const genAI = new GoogleGenerativeAI("your-api-key");
const model = genAI.getGenerativeModel({ model: "gemini-1.5-pro" });
const wrapper = new GeminiWrapper(model);

const response = await wrapper.generateContent("Hello!");
```

## Manual Recording

```typescript
import { TokenTrackrClient } from "token-trackr-sdk";

const client = new TokenTrackrClient();

client.record({
  provider: "bedrock",
  model: "anthropic.claude-3-sonnet",
  promptTokens: 100,
  completionTokens: 50,
  latencyMs: 1500,
});

await client.flush();
```

## Features

### Automatic Host Metadata

The SDK automatically detects:

- **Hostname**: Local machine hostname
- **Cloud Provider**: AWS, Azure, GCP, or on-prem
- **Instance ID**: EC2, Azure VM, or GCE instance ID
- **Kubernetes**: Pod, namespace, and node (if running in K8s)

### Non-Blocking Async Sending

```typescript
const config = new TokenTrackrConfig({
  asyncMode: true, // Enable async mode (default)
  batchSize: 10, // Send after 10 events
  flushInterval: 5, // Or every 5 seconds
  maxQueueSize: 1000, // Maximum events to queue
});
```

### Streaming Support

All wrappers support streaming with automatic token tracking.

## API Reference

### TokenTrackrConfig Options

| Option          | Type    | Default                    | Description               |
| --------------- | ------- | -------------------------- | ------------------------- |
| `backendUrl`    | string  | `$TOKEN_TRACKR_URL`      | Backend API URL           |
| `apiKey`        | string  | `$TOKEN_TRACKR_API_KEY`  | API key for auth          |
| `tenantId`      | string  | `$TOKEN_TRACKR_TENANT_ID`| Tenant identifier         |
| `batchSize`     | number  | 10                         | Events per batch          |
| `flushInterval` | number  | 5                          | Seconds between flushes   |
| `maxQueueSize`  | number  | 1000                       | Max queued events         |
| `retryAttempts` | number  | 3                          | Retry attempts            |
| `timeout`       | number  | 30000                      | Request timeout (ms)      |
| `asyncMode`     | boolean | true                       | Enable async sending      |

## License

MIT

