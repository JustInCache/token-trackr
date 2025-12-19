/**
 * Azure OpenAI Wrapper
 *
 * Wrapper for Azure OpenAI client with automatic token tracking.
 */

import { TokenTrackrClient, getClient } from "../client";

/**
 * Chat message interface
 */
interface ChatMessage {
  role: "system" | "user" | "assistant" | "function" | "tool";
  content: string;
  name?: string;
}

/**
 * Chat completion options
 */
interface ChatCompletionOptions {
  messages: ChatMessage[];
  model?: string;
  maxTokens?: number;
  temperature?: number;
  topP?: number;
  stream?: boolean;
  [key: string]: unknown;
}

/**
 * Chat completion response
 */
interface ChatCompletionResponse {
  id: string;
  choices: Array<{
    message: { role: string; content: string };
    finishReason: string;
  }>;
  usage?: {
    promptTokens: number;
    completionTokens: number;
    totalTokens: number;
  };
}

/**
 * Wrapper for Azure OpenAI client that automatically tracks token usage.
 *
 * @example
 * ```typescript
 * import { OpenAIClient, AzureKeyCredential } from "@azure/openai";
 * import { AzureOpenAIWrapper } from "token-trackr-sdk";
 *
 * const azureClient = new OpenAIClient(
 *   "https://your-resource.openai.azure.com",
 *   new AzureKeyCredential("your-key")
 * );
 * const wrapper = new AzureOpenAIWrapper(azureClient);
 *
 * const response = await wrapper.getChatCompletions(
 *   "gpt-4o",
 *   [{ role: "user", content: "Hello!" }]
 * );
 * ```
 */
export class AzureOpenAIWrapper {
  private azure: unknown;
  private client: TokenTrackrClient;

  constructor(azureClient: unknown, client?: TokenTrackrClient) {
    this.azure = azureClient;
    this.client = client || getClient();
  }

  /**
   * Get chat completions with token tracking.
   */
  async getChatCompletions(
    deploymentName: string,
    messages: ChatMessage[],
    options: Omit<ChatCompletionOptions, "messages"> = {}
  ): Promise<ChatCompletionResponse> {
    const startTime = Date.now();

    const response = await (
      this.azure as {
        getChatCompletions: (
          deployment: string,
          messages: ChatMessage[],
          options?: Record<string, unknown>
        ) => Promise<ChatCompletionResponse>;
      }
    ).getChatCompletions(deploymentName, messages, options);

    const latencyMs = Date.now() - startTime;

    // Extract token usage
    const promptTokens = response.usage?.promptTokens || 0;
    const completionTokens = response.usage?.completionTokens || 0;

    // Record usage
    this.client.record({
      provider: "azure_openai",
      model: deploymentName,
      promptTokens,
      completionTokens,
      latencyMs,
      metadata: {
        id: response.id,
        finishReason: response.choices?.[0]?.finishReason,
      },
    });

    return response;
  }

  /**
   * Stream chat completions with token tracking.
   */
  async *streamChatCompletions(
    deploymentName: string,
    messages: ChatMessage[],
    options: Omit<ChatCompletionOptions, "messages" | "stream"> = {}
  ): AsyncGenerator<unknown, void, unknown> {
    const startTime = Date.now();

    interface StreamEvent {
      choices?: Array<{
        delta?: { content?: string };
        finishReason?: string;
      }>;
      usage?: {
        promptTokens: number;
        completionTokens: number;
      };
    }

    const stream = await (
      this.azure as {
        streamChatCompletions: (
          deployment: string,
          messages: ChatMessage[],
          options?: Record<string, unknown>
        ) => Promise<AsyncIterable<StreamEvent>>;
      }
    ).streamChatCompletions(deploymentName, messages, options);

    let promptTokens = 0;
    let completionTokens = 0;

    for await (const event of stream) {
      // Track usage from stream if available
      if (event.usage) {
        promptTokens = event.usage.promptTokens || 0;
        completionTokens = event.usage.completionTokens || 0;
      }

      yield event;
    }

    // Record usage after stream completes
    const latencyMs = Date.now() - startTime;
    this.client.record({
      provider: "azure_openai",
      model: deploymentName,
      promptTokens,
      completionTokens,
      latencyMs,
    });
  }

  /**
   * Get embeddings with token tracking.
   */
  async getEmbeddings(
    deploymentName: string,
    input: string | string[],
    options: Record<string, unknown> = {}
  ): Promise<unknown> {
    const startTime = Date.now();

    interface EmbeddingsResponse {
      data: Array<{ embedding: number[] }>;
      usage?: { promptTokens: number; totalTokens: number };
    }

    const response = await (
      this.azure as {
        getEmbeddings: (
          deployment: string,
          input: string | string[],
          options?: Record<string, unknown>
        ) => Promise<EmbeddingsResponse>;
      }
    ).getEmbeddings(deploymentName, input, options);

    const latencyMs = Date.now() - startTime;

    // Record usage (embeddings don't have completion tokens)
    this.client.record({
      provider: "azure_openai",
      model: deploymentName,
      promptTokens: response.usage?.promptTokens || 0,
      completionTokens: 0,
      latencyMs,
    });

    return response;
  }
}

