"""
API Tests
=========
Tests for Token Trackr REST API endpoints.
"""

from fastapi.testclient import TestClient


class TestHealthEndpoints:
    """Tests for health check endpoints."""

    def test_health_check(self, client: TestClient):
        """Test liveness probe."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "version" in data


class TestUsageEndpoints:
    """Tests for usage recording endpoints."""

    def test_record_usage(self, client: TestClient, sample_usage_event: dict):
        """Test recording a single usage event."""
        response = client.post("/usage", json=sample_usage_event)
        assert response.status_code == 201
        data = response.json()

        assert data["tenant_id"] == sample_usage_event["tenant_id"]
        assert data["provider"] == sample_usage_event["provider"]
        assert data["model"] == sample_usage_event["model"]
        assert (
            data["total_tokens"]
            == sample_usage_event["prompt_tokens"] + sample_usage_event["completion_tokens"]
        )
        assert "calculated_cost" in data
        assert "id" in data

    def test_record_usage_invalid_provider(self, client: TestClient, sample_usage_event: dict):
        """Test recording with invalid provider."""
        sample_usage_event["provider"] = "invalid_provider"
        response = client.post("/usage", json=sample_usage_event)
        assert response.status_code == 422

    def test_record_usage_missing_required_fields(self, client: TestClient):
        """Test recording with missing fields."""
        response = client.post("/usage", json={"tenant_id": "test"})
        assert response.status_code == 422

    def test_record_batch_usage(self, client: TestClient, sample_batch_events: list[dict]):
        """Test recording multiple usage events."""
        response = client.post("/usage/batch", json=sample_batch_events)
        assert response.status_code == 201
        data = response.json()

        assert len(data) == len(sample_batch_events)
        for item in data:
            assert "id" in item
            assert "calculated_cost" in item


class TestTenantEndpoints:
    """Tests for tenant reporting endpoints."""

    def test_get_tenant_summary_empty(self, client: TestClient):
        """Test getting summary for tenant with no data."""
        response = client.get("/tenant/nonexistent-tenant/summary")
        assert response.status_code == 200
        data = response.json()

        assert data["tenant_id"] == "nonexistent-tenant"
        assert data["total_requests"] == 0
        assert data["total_tokens"] == 0

    def test_get_daily_summary(self, client: TestClient):
        """Test getting daily summary."""
        response = client.get("/tenant/test-tenant/daily")
        assert response.status_code == 200
        data = response.json()

        assert data["tenant_id"] == "test-tenant"
        assert "items" in data
        assert "start_date" in data
        assert "end_date" in data

    def test_get_monthly_summary(self, client: TestClient):
        """Test getting monthly summary."""
        response = client.get("/tenant/test-tenant/monthly")
        assert response.status_code == 200
        data = response.json()

        assert data["tenant_id"] == "test-tenant"
        assert "items" in data


class TestProviderEndpoints:
    """Tests for provider information endpoints."""

    def test_get_bedrock_models(self, client: TestClient):
        """Test getting Bedrock models."""
        response = client.get("/provider/bedrock/models")
        assert response.status_code == 200
        data = response.json()

        assert data["provider"] == "bedrock"
        assert "models" in data

    def test_get_azure_models(self, client: TestClient):
        """Test getting Azure OpenAI models."""
        response = client.get("/provider/azure_openai/models")
        assert response.status_code == 200
        data = response.json()

        assert data["provider"] == "azure_openai"

    def test_get_gemini_models(self, client: TestClient):
        """Test getting Gemini models."""
        response = client.get("/provider/gemini/models")
        assert response.status_code == 200
        data = response.json()

        assert data["provider"] == "gemini"

    def test_get_invalid_provider(self, client: TestClient):
        """Test getting models for invalid provider."""
        response = client.get("/provider/invalid/models")
        assert response.status_code == 400
