/**
 * Host Metadata Collection
 */

import { readFileSync, existsSync } from "fs";
import { hostname } from "os";

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

/**
 * Check if running inside a Kubernetes pod
 */
function isRunningInKubernetes(): boolean {
  return existsSync("/var/run/secrets/kubernetes.io/serviceaccount/token");
}

/**
 * Get Kubernetes metadata from environment
 */
function getK8sMetadata(): K8sMetadata | undefined {
  if (!isRunningInKubernetes()) {
    return undefined;
  }

  let namespace: string | undefined;
  try {
    namespace = readFileSync(
      "/var/run/secrets/kubernetes.io/serviceaccount/namespace",
      "utf8"
    ).trim();
  } catch {
    namespace = process.env.POD_NAMESPACE;
  }

  return {
    pod: process.env.HOSTNAME || process.env.POD_NAME,
    namespace,
    node: process.env.NODE_NAME,
  };
}

/**
 * Detect if running on AWS and get instance ID
 */
async function detectAWS(): Promise<[boolean, string | undefined]> {
  try {
    // Use IMDSv2
    const tokenResponse = await fetch(
      "http://169.254.169.254/latest/api/token",
      {
        method: "PUT",
        headers: { "X-aws-ec2-metadata-token-ttl-seconds": "21600" },
        signal: AbortSignal.timeout(1000),
      }
    );
    const token = await tokenResponse.text();

    const instanceResponse = await fetch(
      "http://169.254.169.254/latest/meta-data/instance-id",
      {
        headers: { "X-aws-ec2-metadata-token": token },
        signal: AbortSignal.timeout(1000),
      }
    );
    const instanceId = await instanceResponse.text();

    return [true, instanceId];
  } catch {
    return [false, undefined];
  }
}

/**
 * Detect if running on Azure and get instance ID
 */
async function detectAzure(): Promise<[boolean, string | undefined]> {
  try {
    const response = await fetch(
      "http://169.254.169.254/metadata/instance/compute/vmId?api-version=2021-02-01&format=text",
      {
        headers: { Metadata: "true" },
        signal: AbortSignal.timeout(1000),
      }
    );
    const instanceId = await response.text();

    return [true, instanceId];
  } catch {
    return [false, undefined];
  }
}

/**
 * Detect if running on GCP and get instance ID
 */
async function detectGCP(): Promise<[boolean, string | undefined]> {
  try {
    const response = await fetch(
      "http://metadata.google.internal/computeMetadata/v1/instance/id",
      {
        headers: { "Metadata-Flavor": "Google" },
        signal: AbortSignal.timeout(1000),
      }
    );
    const instanceId = await response.text();

    return [true, instanceId];
  } catch {
    return [false, undefined];
  }
}

/**
 * Collect metadata about the current host environment.
 *
 * Detects:
 * - Hostname
 * - Cloud provider (AWS, Azure, GCP, or on-prem)
 * - Instance ID (for cloud VMs)
 * - Kubernetes metadata (if running in K8s)
 */
export async function getHostMetadata(): Promise<HostMetadata> {
  const metadata: HostMetadata = {
    hostname: hostname(),
    cloudProvider: "unknown",
  };

  // Check for Kubernetes
  metadata.k8s = getK8sMetadata();

  // Detect cloud provider
  const [isAWS, awsInstance] = await detectAWS();
  if (isAWS) {
    metadata.cloudProvider = "aws";
    metadata.instanceId = awsInstance;
    return metadata;
  }

  const [isAzure, azureInstance] = await detectAzure();
  if (isAzure) {
    metadata.cloudProvider = "azure";
    metadata.instanceId = azureInstance;
    return metadata;
  }

  const [isGCP, gcpInstance] = await detectGCP();
  if (isGCP) {
    metadata.cloudProvider = "gcp";
    metadata.instanceId = gcpInstance;
    return metadata;
  }

  // On-prem or unknown
  metadata.cloudProvider = "on-prem";
  return metadata;
}

/**
 * Get host metadata synchronously (cached or with defaults)
 */
let cachedMetadata: HostMetadata | null = null;

export function getHostMetadataSync(): HostMetadata {
  if (cachedMetadata) {
    return cachedMetadata;
  }

  // Return basic metadata synchronously
  return {
    hostname: hostname(),
    cloudProvider: "unknown",
    k8s: getK8sMetadata(),
  };
}

/**
 * Initialize and cache host metadata
 */
export async function initHostMetadata(): Promise<HostMetadata> {
  cachedMetadata = await getHostMetadata();
  return cachedMetadata;
}

