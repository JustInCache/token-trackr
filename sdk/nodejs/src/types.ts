/**
 * Type definitions for the Token Trackr SDK
 */

export interface K8sMetadata {
  pod?: string;
  namespace?: string;
  node?: string;
}

export interface HostMetadata {
  hostname: string;
  cloudProvider: "aws" | "azure" | "gcp" | "on-prem" | "unknown";
  instanceId?: string;
  k8s?: K8sMetadata;
}

export interface UsageEvent {
  tenantId: string;
  provider: "bedrock" | "azure_openai" | "gemini";
  model: string;
  promptTokens: number;
  completionTokens: number;
  timestamp: Date;
  latencyMs?: number;
  host?: HostMetadata;
  metadata?: Record<string, unknown>;
}

export interface UsageResponse {
  id: string;
  tenantId: string;
  provider: string;
  model: string;
  totalTokens: number;
  calculatedCost: number;
  timestamp: Date;
}

export interface UsageEventPayload {
  tenant_id: string;
  provider: string;
  model: string;
  prompt_tokens: number;
  completion_tokens: number;
  timestamp: string;
  latency_ms?: number;
  host?: {
    hostname: string;
    cloud_provider: string;
    instance_id?: string;
    k8s?: {
      pod?: string;
      namespace?: string;
      node?: string;
    };
  };
  metadata?: Record<string, unknown>;
}

