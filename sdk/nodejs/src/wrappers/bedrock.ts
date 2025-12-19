/**
 * AWS Bedrock Wrapper
 *
 * Wrapper for AWS Bedrock client with automatic token tracking.
 */

import { TokenTrackrClient, getClient } from "../client";

/**
 * Bedrock invoke model command input
 */
interface InvokeModelInput {
  modelId: string;
  body: string | Uint8Array;
  contentType?: string;
  accept?: string;
}

/**
 * Bedrock invoke model response
 */
interface InvokeModelResponse {
  body: Uint8Array;
  contentType?: string;
  $metadata?: {
    requestId?: string;
  };
}

/**
 * Wrapper for AWS Bedrock client that automatically tracks token usage.
 *
 * @example
 * ```typescript
 * import { BedrockRuntimeClient, InvokeModelCommand } from "@aws-sdk/client-bedrock-runtime";
 * import { BedrockWrapper } from "token-trackr-sdk";
 *
 * const bedrock = new BedrockRuntimeClient({ region: "us-east-1" });
 * const wrapper = new BedrockWrapper(bedrock);
 *
 * const response = await wrapper.invokeModel({
 *   modelId: "anthropic.claude-3-sonnet-20240229-v1:0",
 *   body: JSON.stringify({
 *     messages: [{ role: "user", content: "Hello!" }],
 *     max_tokens: 100,
 *   }),
 * });
 * ```
 */
export class BedrockWrapper {
  private bedrock: unknown;
  private client: TokenTrackrClient;

  constructor(bedrockClient: unknown, client?: TokenTrackrClient) {
    this.bedrock = bedrockClient;
    this.client = client || getClient();
  }

  /**
   * Invoke a Bedrock model with token tracking.
   */
  async invokeModel(
    input: InvokeModelInput
  ): Promise<{ body: unknown; raw: InvokeModelResponse }> {
    const startTime = Date.now();

    // Import dynamically to avoid requiring the SDK
    const { InvokeModelCommand } = await import(
      "@aws-sdk/client-bedrock-runtime"
    );

    const command = new InvokeModelCommand({
      modelId: input.modelId,
      body: input.body,
      contentType: input.contentType || "application/json",
      accept: input.accept || "application/json",
    });

    const response = await (this.bedrock as { send: (cmd: unknown) => Promise<InvokeModelResponse> }).send(command);
    const latencyMs = Date.now() - startTime;

    // Parse response body
    const responseBody = JSON.parse(new TextDecoder().decode(response.body));

    // Extract token counts
    const [promptTokens, completionTokens] = this.extractTokens(
      input.modelId,
      responseBody
    );

    // Record usage
    this.client.record({
      provider: "bedrock",
      model: input.modelId,
      promptTokens,
      completionTokens,
      latencyMs,
      metadata: {
        requestId: response.$metadata?.requestId,
      },
    });

    return { body: responseBody, raw: response };
  }

  /**
   * Extract token counts from response based on model family.
   */
  private extractTokens(
    modelId: string,
    responseBody: Record<string, unknown>
  ): [number, number] {
    const modelIdLower = modelId.toLowerCase();

    // Anthropic Claude models
    if (modelIdLower.includes("anthropic")) {
      const usage = responseBody.usage as
        | { input_tokens?: number; output_tokens?: number }
        | undefined;
      return [usage?.input_tokens || 0, usage?.output_tokens || 0];
    }

    // Amazon Titan models
    if (modelIdLower.includes("amazon.titan")) {
      const results = responseBody.results as Array<{ tokenCount?: number }> | undefined;
      return [
        (responseBody.inputTextTokenCount as number) || 0,
        results?.[0]?.tokenCount || 0,
      ];
    }

    // Meta Llama models
    if (modelIdLower.includes("meta.llama")) {
      return [
        (responseBody.prompt_token_count as number) || 0,
        (responseBody.generation_token_count as number) || 0,
      ];
    }

    // Cohere models
    if (modelIdLower.includes("cohere")) {
      const meta = responseBody.meta as
        | { billed_units?: { input_tokens?: number; output_tokens?: number } }
        | undefined;
      return [
        meta?.billed_units?.input_tokens || 0,
        meta?.billed_units?.output_tokens || 0,
      ];
    }

    // Mistral models
    if (modelIdLower.includes("mistral")) {
      const usage = responseBody.usage as
        | { prompt_tokens?: number; completion_tokens?: number }
        | undefined;
      return [usage?.prompt_tokens || 0, usage?.completion_tokens || 0];
    }

    // AI21 models
    if (modelIdLower.includes("ai21")) {
      const usage = responseBody.usage as
        | { prompt_tokens?: number; completion_tokens?: number }
        | undefined;
      return [usage?.prompt_tokens || 0, usage?.completion_tokens || 0];
    }

    return [0, 0];
  }

  /**
   * Invoke a Bedrock model with streaming.
   * Note: Token tracking happens after stream completes.
   */
  async *invokeModelWithResponseStream(
    input: InvokeModelInput
  ): AsyncGenerator<unknown, void, unknown> {
    const startTime = Date.now();

    const { InvokeModelWithResponseStreamCommand } = await import(
      "@aws-sdk/client-bedrock-runtime"
    );

    const command = new InvokeModelWithResponseStreamCommand({
      modelId: input.modelId,
      body: input.body,
      contentType: input.contentType || "application/json",
    });

    interface StreamResponse {
      body: AsyncIterable<{ chunk?: { bytes: Uint8Array } }>;
    }

    const response = await (this.bedrock as { send: (cmd: unknown) => Promise<StreamResponse> }).send(command);

    let promptTokens = 0;
    let completionTokens = 0;

    for await (const event of response.body) {
      if (event.chunk?.bytes) {
        const chunkData = JSON.parse(
          new TextDecoder().decode(event.chunk.bytes)
        );

        // Extract token counts from final message
        if (chunkData.type === "message_stop") {
          const metrics = chunkData["amazon-bedrock-invocationMetrics"];
          if (metrics) {
            promptTokens = metrics.inputTokenCount || 0;
            completionTokens = metrics.outputTokenCount || 0;
          }
        }

        yield chunkData;
      }
    }

    // Record usage after stream completes
    const latencyMs = Date.now() - startTime;
    this.client.record({
      provider: "bedrock",
      model: input.modelId,
      promptTokens,
      completionTokens,
      latencyMs,
    });
  }
}

