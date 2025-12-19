/**
 * Token Trackr Client
 *
 * Main client for sending usage events to the backend.
 */

import { writeFileSync, mkdirSync } from "fs";
import { join } from "path";
import { homedir } from "os";
import { TokenTrackrConfig, TokenTrackrOptions } from "./config";
import {
  getHostMetadata,
  getHostMetadataSync,
  initHostMetadata,
  HostMetadata,
} from "./metadata";
import { UsageEvent, UsageEventPayload, UsageResponse } from "./types";

export class TokenTrackrClient {
  private config: TokenTrackrConfig;
  private queue: UsageEvent[] = [];
  private hostMetadata: HostMetadata | null = null;
  private flushTimer: ReturnType<typeof setInterval> | null = null;
  private closed = false;

  constructor(options?: TokenTrackrOptions | TokenTrackrConfig) {
    this.config =
      options instanceof TokenTrackrConfig
        ? options
        : new TokenTrackrConfig(options);

    // Start background flush if async mode
    if (this.config.asyncMode) {
      this.startBackgroundFlush();
    }

    // Initialize host metadata in background
    this.initMetadata();

    // Register cleanup
    process.on("exit", () => this.close());
    process.on("SIGINT", () => this.close());
    process.on("SIGTERM", () => this.close());
  }

  private async initMetadata(): Promise<void> {
    this.hostMetadata = await initHostMetadata();
  }

  private startBackgroundFlush(): void {
    this.flushTimer = setInterval(() => {
      this.flush().catch((err) => {
        console.error("[TokenTrackr] Background flush failed:", err);
      });
    }, this.config.flushInterval * 1000);
  }

  private getHeaders(): Record<string, string> {
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      "User-Agent": "token-trackr-sdk-nodejs/1.0.0",
    };
    if (this.config.apiKey) {
      headers["Authorization"] = `Bearer ${this.config.apiKey}`;
    }
    return headers;
  }

  /**
   * Record a token usage event.
   */
  record(options: {
    provider: "bedrock" | "azure_openai" | "gemini";
    model: string;
    promptTokens: number;
    completionTokens: number;
    latencyMs?: number;
    metadata?: Record<string, unknown>;
    timestamp?: Date;
  }): void {
    const event: UsageEvent = {
      tenantId: this.config.tenantId,
      provider: options.provider,
      model: options.model,
      promptTokens: options.promptTokens,
      completionTokens: options.completionTokens,
      timestamp: options.timestamp || new Date(),
      latencyMs: options.latencyMs,
      host: this.hostMetadata || getHostMetadataSync(),
      metadata: options.metadata,
    };

    // Add to queue
    if (this.queue.length < this.config.maxQueueSize) {
      this.queue.push(event);
    }

    // Flush if batch size reached
    if (this.queue.length >= this.config.batchSize) {
      if (this.config.asyncMode) {
        this.flush().catch((err) => {
          console.error("[TokenTrackr] Flush failed:", err);
        });
      } else {
        // Sync mode - would block, so just log
        this.flush().catch((err) => {
          console.error("[TokenTrackr] Flush failed:", err);
        });
      }
    }
  }

  /**
   * Flush all queued events to the backend.
   */
  async flush(): Promise<UsageResponse[]> {
    if (this.queue.length === 0) {
      return [];
    }

    const events = [...this.queue];
    this.queue = [];

    try {
      return await this.sendBatch(events);
    } catch (err) {
      console.error("[TokenTrackr] Failed to send events:", err);

      // Put events back in queue
      for (const event of events) {
        if (this.queue.length < this.config.maxQueueSize) {
          this.queue.unshift(event);
        }
      }

      // Save to fallback
      this.saveToFallback(events);
      return [];
    }
  }

  private async sendBatch(
    events: UsageEvent[],
    attempt = 1
  ): Promise<UsageResponse[]> {
    const payloads = events.map(this.eventToPayload);

    const url =
      events.length === 1
        ? `${this.config.backendUrl}/usage`
        : `${this.config.backendUrl}/usage/batch`;

    const body = events.length === 1 ? payloads[0] : payloads;

    const response = await fetch(url, {
      method: "POST",
      headers: this.getHeaders(),
      body: JSON.stringify(body),
      signal: AbortSignal.timeout(this.config.timeout),
    });

    if (!response.ok) {
      if (attempt < this.config.retryAttempts) {
        // Exponential backoff
        await new Promise((r) =>
          setTimeout(r, Math.min(1000 * Math.pow(2, attempt), 10000))
        );
        return this.sendBatch(events, attempt + 1);
      }
      throw new Error(`HTTP ${response.status}: ${await response.text()}`);
    }

    const data = await response.json();
    return Array.isArray(data) ? data : [data];
  }

  private eventToPayload(event: UsageEvent): UsageEventPayload {
    return {
      tenant_id: event.tenantId,
      provider: event.provider,
      model: event.model,
      prompt_tokens: event.promptTokens,
      completion_tokens: event.completionTokens,
      timestamp: event.timestamp.toISOString(),
      latency_ms: event.latencyMs,
      host: event.host
        ? {
            hostname: event.host.hostname,
            cloud_provider: event.host.cloudProvider,
            instance_id: event.host.instanceId,
            k8s: event.host.k8s
              ? {
                  pod: event.host.k8s.pod,
                  namespace: event.host.k8s.namespace,
                  node: event.host.k8s.node,
                }
              : undefined,
          }
        : undefined,
      metadata: event.metadata,
    };
  }

  private saveToFallback(events: UsageEvent[]): void {
    try {
      const fallbackDir = join(homedir(), ".token-trackr", "fallback");
      mkdirSync(fallbackDir, { recursive: true });

      const fallbackFile = join(fallbackDir, `events_${Date.now()}.json`);
      writeFileSync(
        fallbackFile,
        JSON.stringify(events.map(this.eventToPayload), null, 2)
      );

      console.log(
        `[TokenTrackr] Saved ${events.length} events to fallback: ${fallbackFile}`
      );
    } catch (err) {
      console.error("[TokenTrackr] Failed to save fallback:", err);
    }
  }

  /**
   * Close the client and flush remaining events.
   */
  async close(): Promise<void> {
    if (this.closed) return;
    this.closed = true;

    if (this.flushTimer) {
      clearInterval(this.flushTimer);
      this.flushTimer = null;
    }

    try {
      await this.flush();
    } catch (err) {
      console.error("[TokenTrackr] Final flush failed:", err);
    }
  }
}

// Global client instance
let globalClient: TokenTrackrClient | null = null;

/**
 * Get or create the global client instance.
 */
export function getClient(): TokenTrackrClient {
  if (!globalClient) {
    globalClient = new TokenTrackrClient();
  }
  return globalClient;
}

/**
 * Record a usage event using the global client.
 */
export function record(options: {
  provider: "bedrock" | "azure_openai" | "gemini";
  model: string;
  promptTokens: number;
  completionTokens: number;
  latencyMs?: number;
  metadata?: Record<string, unknown>;
}): void {
  getClient().record(options);
}

