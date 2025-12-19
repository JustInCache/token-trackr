/**
 * Google Gemini Wrapper
 *
 * Wrapper for Google Gemini client with automatic token tracking.
 */

import { TokenTrackrClient, getClient } from "../client";

/**
 * Gemini content part
 */
interface ContentPart {
  text?: string;
  inlineData?: { mimeType: string; data: string };
}

/**
 * Gemini generation response
 */
interface GenerateContentResponse {
  response: {
    candidates?: Array<{
      content: { parts: ContentPart[] };
      finishReason?: string;
    }>;
    usageMetadata?: {
      promptTokenCount: number;
      candidatesTokenCount: number;
      totalTokenCount: number;
    };
  };
}

/**
 * Gemini model interface
 */
interface GeminiModel {
  model: string;
  generateContent: (
    contents: string | ContentPart[]
  ) => Promise<GenerateContentResponse>;
  generateContentStream: (
    contents: string | ContentPart[]
  ) => Promise<AsyncIterable<GenerateContentResponse>>;
  countTokens: (contents: string | ContentPart[]) => Promise<{ totalTokens: number }>;
  startChat: (options?: Record<string, unknown>) => ChatSession;
}

/**
 * Chat session interface
 */
interface ChatSession {
  sendMessage: (
    content: string | ContentPart[]
  ) => Promise<GenerateContentResponse>;
  sendMessageStream: (
    content: string | ContentPart[]
  ) => Promise<AsyncIterable<GenerateContentResponse>>;
  getHistory: () => unknown[];
}

/**
 * Wrapper for Google Gemini client that automatically tracks token usage.
 *
 * @example
 * ```typescript
 * import { GoogleGenerativeAI } from "@google/generative-ai";
 * import { GeminiWrapper } from "token-trackr-sdk";
 *
 * const genAI = new GoogleGenerativeAI("your-api-key");
 * const model = genAI.getGenerativeModel({ model: "gemini-1.5-pro" });
 * const wrapper = new GeminiWrapper(model);
 *
 * const response = await wrapper.generateContent("Hello!");
 * ```
 */
export class GeminiWrapper {
  private model: GeminiModel;
  private modelName: string;
  private client: TokenTrackrClient;

  constructor(model: GeminiModel, client?: TokenTrackrClient) {
    this.model = model;
    this.modelName = model.model || "gemini-unknown";
    this.client = client || getClient();
  }

  /**
   * Generate content with token tracking.
   */
  async generateContent(
    contents: string | ContentPart[]
  ): Promise<GenerateContentResponse> {
    const startTime = Date.now();

    const response = await this.model.generateContent(contents);

    const latencyMs = Date.now() - startTime;

    // Extract token usage
    const usage = response.response.usageMetadata;
    const promptTokens = usage?.promptTokenCount || 0;
    const completionTokens = usage?.candidatesTokenCount || 0;

    // Record usage
    this.client.record({
      provider: "gemini",
      model: this.modelName,
      promptTokens,
      completionTokens,
      latencyMs,
      metadata: {
        finishReason: response.response.candidates?.[0]?.finishReason,
      },
    });

    return response;
  }

  /**
   * Generate content with streaming and token tracking.
   */
  async *generateContentStream(
    contents: string | ContentPart[]
  ): AsyncGenerator<GenerateContentResponse, void, unknown> {
    const startTime = Date.now();

    const stream = await this.model.generateContentStream(contents);

    let promptTokens = 0;
    let completionTokens = 0;

    for await (const chunk of stream) {
      // Update token counts from usage metadata
      const usage = chunk.response.usageMetadata;
      if (usage) {
        promptTokens = usage.promptTokenCount || 0;
        completionTokens = usage.candidatesTokenCount || 0;
      }

      yield chunk;
    }

    // Record usage after stream completes
    const latencyMs = Date.now() - startTime;
    this.client.record({
      provider: "gemini",
      model: this.modelName,
      promptTokens,
      completionTokens,
      latencyMs,
    });
  }

  /**
   * Count tokens in content (no usage tracking).
   */
  async countTokens(
    contents: string | ContentPart[]
  ): Promise<{ totalTokens: number }> {
    return this.model.countTokens(contents);
  }

  /**
   * Start a chat session with token tracking.
   */
  startChat(options?: Record<string, unknown>): GeminiChatSession {
    const chat = this.model.startChat(options);
    return new GeminiChatSession(chat, this.modelName, this.client);
  }
}

/**
 * Wrapped Gemini chat session with token tracking.
 */
class GeminiChatSession {
  private chat: ChatSession;
  private modelName: string;
  private client: TokenTrackrClient;

  constructor(
    chat: ChatSession,
    modelName: string,
    client: TokenTrackrClient
  ) {
    this.chat = chat;
    this.modelName = modelName;
    this.client = client;
  }

  /**
   * Send a message with token tracking.
   */
  async sendMessage(
    content: string | ContentPart[]
  ): Promise<GenerateContentResponse> {
    const startTime = Date.now();

    const response = await this.chat.sendMessage(content);

    const latencyMs = Date.now() - startTime;

    // Extract token usage
    const usage = response.response.usageMetadata;
    const promptTokens = usage?.promptTokenCount || 0;
    const completionTokens = usage?.candidatesTokenCount || 0;

    // Record usage
    this.client.record({
      provider: "gemini",
      model: this.modelName,
      promptTokens,
      completionTokens,
      latencyMs,
    });

    return response;
  }

  /**
   * Send a message with streaming and token tracking.
   */
  async *sendMessageStream(
    content: string | ContentPart[]
  ): AsyncGenerator<GenerateContentResponse, void, unknown> {
    const startTime = Date.now();

    const stream = await this.chat.sendMessageStream(content);

    let promptTokens = 0;
    let completionTokens = 0;

    for await (const chunk of stream) {
      const usage = chunk.response.usageMetadata;
      if (usage) {
        promptTokens = usage.promptTokenCount || 0;
        completionTokens = usage.candidatesTokenCount || 0;
      }

      yield chunk;
    }

    // Record usage after stream completes
    const latencyMs = Date.now() - startTime;
    this.client.record({
      provider: "gemini",
      model: this.modelName,
      promptTokens,
      completionTokens,
      latencyMs,
    });
  }

  /**
   * Get chat history.
   */
  getHistory(): unknown[] {
    return this.chat.getHistory();
  }
}

