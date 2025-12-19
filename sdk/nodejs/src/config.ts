/**
 * SDK Configuration
 */

export interface TokenTrackrOptions {
  /**
   * URL of the Token Trackr backend
   * @default process.env.TOKEN_TRACKR_URL || "http://localhost:8000"
   */
  backendUrl?: string;

  /**
   * API key for authentication
   * @default process.env.TOKEN_TRACKR_API_KEY
   */
  apiKey?: string;

  /**
   * Tenant identifier for multi-tenancy
   * @default process.env.TOKEN_TRACKR_TENANT_ID || "default"
   */
  tenantId?: string;

  /**
   * Number of events to batch before sending
   * @default 10
   */
  batchSize?: number;

  /**
   * Seconds between automatic flushes
   * @default 5
   */
  flushInterval?: number;

  /**
   * Maximum events to queue locally
   * @default 1000
   */
  maxQueueSize?: number;

  /**
   * Number of retry attempts for failed requests
   * @default 3
   */
  retryAttempts?: number;

  /**
   * Request timeout in milliseconds
   * @default 30000
   */
  timeout?: number;

  /**
   * Enable non-blocking async event sending
   * @default true
   */
  asyncMode?: boolean;
}

export class TokenTrackrConfig {
  readonly backendUrl: string;
  readonly apiKey?: string;
  readonly tenantId: string;
  readonly batchSize: number;
  readonly flushInterval: number;
  readonly maxQueueSize: number;
  readonly retryAttempts: number;
  readonly timeout: number;
  readonly asyncMode: boolean;

  constructor(options: TokenTrackrOptions = {}) {
    this.backendUrl = (
      options.backendUrl ||
      process.env.TOKEN_TRACKR_URL ||
      "http://localhost:8000"
    ).replace(/\/$/, "");

    this.apiKey = options.apiKey || process.env.TOKEN_TRACKR_API_KEY;

    this.tenantId =
      options.tenantId ||
      process.env.TOKEN_TRACKR_TENANT_ID ||
      "default";

    this.batchSize = options.batchSize ?? 10;
    this.flushInterval = options.flushInterval ?? 5;
    this.maxQueueSize = options.maxQueueSize ?? 1000;
    this.retryAttempts = options.retryAttempts ?? 3;
    this.timeout = options.timeout ?? 30000;
    this.asyncMode = options.asyncMode ?? true;

    if (!this.backendUrl) {
      throw new Error("backendUrl is required");
    }
    if (!this.tenantId) {
      throw new Error("tenantId is required");
    }
  }
}

