"""
Host Metadata Collection
========================
Collect metadata about the host environment.
"""

import os
import socket
from dataclasses import dataclass
from typing import Optional

import httpx


@dataclass
class K8sMetadata:
    """Kubernetes metadata."""

    pod: Optional[str] = None
    namespace: Optional[str] = None
    node: Optional[str] = None


@dataclass
class HostMetadata:
    """Host environment metadata."""

    hostname: str = ""
    cloud_provider: str = "unknown"
    instance_id: Optional[str] = None
    k8s: Optional[K8sMetadata] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for API requests."""
        result = {
            "hostname": self.hostname,
            "cloud_provider": self.cloud_provider,
            "instance_id": self.instance_id,
        }
        if self.k8s:
            result["k8s"] = {
                "pod": self.k8s.pod,
                "namespace": self.k8s.namespace,
                "node": self.k8s.node,
            }
        return result


def _is_running_in_kubernetes() -> bool:
    """Check if running inside a Kubernetes pod."""
    return os.path.exists("/var/run/secrets/kubernetes.io/serviceaccount/token")


def _get_k8s_metadata() -> Optional[K8sMetadata]:
    """Get Kubernetes metadata from environment."""
    if not _is_running_in_kubernetes():
        return None

    return K8sMetadata(
        pod=os.getenv("HOSTNAME") or os.getenv("POD_NAME"),
        namespace=os.getenv("POD_NAMESPACE") or _read_k8s_namespace(),
        node=os.getenv("NODE_NAME"),
    )


def _read_k8s_namespace() -> Optional[str]:
    """Read namespace from Kubernetes service account."""
    try:
        with open("/var/run/secrets/kubernetes.io/serviceaccount/namespace") as f:
            return f.read().strip()
    except Exception:
        return None


def _detect_aws() -> tuple[bool, Optional[str]]:
    """Detect if running on AWS and get instance ID."""
    try:
        # Use IMDSv2
        token_response = httpx.put(
            "http://169.254.169.254/latest/api/token",
            headers={"X-aws-ec2-metadata-token-ttl-seconds": "21600"},
            timeout=1.0,
        )
        token = token_response.text

        instance_response = httpx.get(
            "http://169.254.169.254/latest/meta-data/instance-id",
            headers={"X-aws-ec2-metadata-token": token},
            timeout=1.0,
        )
        return True, instance_response.text
    except Exception:
        return False, None


def _detect_azure() -> tuple[bool, Optional[str]]:
    """Detect if running on Azure and get instance ID."""
    try:
        response = httpx.get(
            "http://169.254.169.254/metadata/instance/compute/vmId",
            params={"api-version": "2021-02-01", "format": "text"},
            headers={"Metadata": "true"},
            timeout=1.0,
        )
        return True, response.text
    except Exception:
        return False, None


def _detect_gcp() -> tuple[bool, Optional[str]]:
    """Detect if running on GCP and get instance ID."""
    try:
        response = httpx.get(
            "http://metadata.google.internal/computeMetadata/v1/instance/id",
            headers={"Metadata-Flavor": "Google"},
            timeout=1.0,
        )
        return True, response.text
    except Exception:
        return False, None


def get_host_metadata() -> HostMetadata:
    """
    Collect metadata about the current host environment.

    Detects:
    - Hostname
    - Cloud provider (AWS, Azure, GCP, or on-prem)
    - Instance ID (for cloud VMs)
    - Kubernetes metadata (if running in K8s)

    Returns:
        HostMetadata object with collected information
    """
    metadata = HostMetadata(
        hostname=socket.gethostname(),
    )

    # Check for Kubernetes
    metadata.k8s = _get_k8s_metadata()

    # Detect cloud provider
    is_aws, aws_instance = _detect_aws()
    if is_aws:
        metadata.cloud_provider = "aws"
        metadata.instance_id = aws_instance
        return metadata

    is_azure, azure_instance = _detect_azure()
    if is_azure:
        metadata.cloud_provider = "azure"
        metadata.instance_id = azure_instance
        return metadata

    is_gcp, gcp_instance = _detect_gcp()
    if is_gcp:
        metadata.cloud_provider = "gcp"
        metadata.instance_id = gcp_instance
        return metadata

    # On-prem or unknown
    metadata.cloud_provider = "on-prem"
    return metadata
