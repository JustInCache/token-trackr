-- Token Trackr Database Initialization
-- ======================================
-- This script is executed when the PostgreSQL container starts
-- for the first time using Docker Compose.

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Create the token_usage_raw table
CREATE TABLE IF NOT EXISTS token_usage_raw (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id VARCHAR(255) NOT NULL,
    provider VARCHAR(50) NOT NULL,
    model VARCHAR(255) NOT NULL,
    prompt_tokens BIGINT NOT NULL,
    completion_tokens BIGINT NOT NULL,
    total_tokens BIGINT NOT NULL,
    calculated_cost NUMERIC(20, 10) NOT NULL DEFAULT 0,
    timestamp TIMESTAMPTZ NOT NULL,
    latency_ms BIGINT,
    cloud_provider VARCHAR(50) NOT NULL DEFAULT 'unknown',
    hostname VARCHAR(255),
    instance_id VARCHAR(255),
    k8s_pod VARCHAR(255),
    k8s_namespace VARCHAR(255),
    k8s_node VARCHAR(255),
    metadata_json TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Create indexes for token_usage_raw
CREATE INDEX IF NOT EXISTS idx_usage_tenant_id ON token_usage_raw(tenant_id);
CREATE INDEX IF NOT EXISTS idx_usage_provider ON token_usage_raw(provider);
CREATE INDEX IF NOT EXISTS idx_usage_model ON token_usage_raw(model);
CREATE INDEX IF NOT EXISTS idx_usage_timestamp ON token_usage_raw(timestamp);
CREATE INDEX IF NOT EXISTS idx_usage_tenant_timestamp ON token_usage_raw(tenant_id, timestamp);
CREATE INDEX IF NOT EXISTS idx_usage_provider_model ON token_usage_raw(provider, model);
CREATE INDEX IF NOT EXISTS idx_usage_cloud_instance ON token_usage_raw(cloud_provider, instance_id);
CREATE INDEX IF NOT EXISTS idx_usage_k8s ON token_usage_raw(k8s_namespace, k8s_pod);

-- Create tenant_daily_summary table
CREATE TABLE IF NOT EXISTS tenant_daily_summary (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id VARCHAR(255) NOT NULL,
    date DATE NOT NULL,
    provider VARCHAR(50) NOT NULL,
    model VARCHAR(255) NOT NULL,
    cloud_provider VARCHAR(50) NOT NULL,
    total_requests BIGINT NOT NULL DEFAULT 0,
    total_prompt_tokens BIGINT NOT NULL DEFAULT 0,
    total_completion_tokens BIGINT NOT NULL DEFAULT 0,
    total_tokens BIGINT NOT NULL DEFAULT 0,
    total_cost NUMERIC(20, 10) NOT NULL DEFAULT 0,
    avg_latency_ms BIGINT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_daily_summary UNIQUE (tenant_id, date, provider, model, cloud_provider)
);

CREATE INDEX IF NOT EXISTS idx_daily_tenant_date ON tenant_daily_summary(tenant_id, date);

-- Create tenant_monthly_summary table
CREATE TABLE IF NOT EXISTS tenant_monthly_summary (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id VARCHAR(255) NOT NULL,
    year INTEGER NOT NULL,
    month INTEGER NOT NULL,
    provider VARCHAR(50) NOT NULL,
    model VARCHAR(255) NOT NULL,
    total_requests BIGINT NOT NULL DEFAULT 0,
    total_prompt_tokens BIGINT NOT NULL DEFAULT 0,
    total_completion_tokens BIGINT NOT NULL DEFAULT 0,
    total_tokens BIGINT NOT NULL DEFAULT 0,
    total_cost NUMERIC(20, 10) NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_monthly_summary UNIQUE (tenant_id, year, month, provider, model)
);

CREATE INDEX IF NOT EXISTS idx_monthly_tenant_period ON tenant_monthly_summary(tenant_id, year, month);

-- Create pricing_table
CREATE TABLE IF NOT EXISTS pricing_table (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    provider VARCHAR(50) NOT NULL,
    model VARCHAR(255) NOT NULL,
    input_price_per_1k NUMERIC(20, 10) NOT NULL,
    output_price_per_1k NUMERIC(20, 10) NOT NULL,
    effective_from DATE NOT NULL,
    effective_to DATE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_pricing_model_date UNIQUE (provider, model, effective_from)
);

CREATE INDEX IF NOT EXISTS idx_pricing_lookup ON pricing_table(provider, model, is_active);

-- Create function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for updated_at
DROP TRIGGER IF EXISTS update_token_usage_raw_updated_at ON token_usage_raw;
CREATE TRIGGER update_token_usage_raw_updated_at
    BEFORE UPDATE ON token_usage_raw
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_tenant_daily_summary_updated_at ON tenant_daily_summary;
CREATE TRIGGER update_tenant_daily_summary_updated_at
    BEFORE UPDATE ON tenant_daily_summary
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_tenant_monthly_summary_updated_at ON tenant_monthly_summary;
CREATE TRIGGER update_tenant_monthly_summary_updated_at
    BEFORE UPDATE ON tenant_monthly_summary
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_pricing_table_updated_at ON pricing_table;
CREATE TRIGGER update_pricing_table_updated_at
    BEFORE UPDATE ON pricing_table
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Insert some sample pricing data
INSERT INTO pricing_table (provider, model, input_price_per_1k, output_price_per_1k, effective_from)
VALUES 
    ('bedrock', 'anthropic.claude-3-5-sonnet-20241022-v2:0', 0.003, 0.015, '2024-01-01'),
    ('bedrock', 'anthropic.claude-3-haiku-20240307-v1:0', 0.00025, 0.00125, '2024-01-01'),
    ('azure_openai', 'gpt-4o', 0.005, 0.015, '2024-01-01'),
    ('azure_openai', 'gpt-4o-mini', 0.00015, 0.0006, '2024-01-01'),
    ('gemini', 'gemini-1.5-pro', 0.00125, 0.005, '2024-01-01'),
    ('gemini', 'gemini-1.5-flash', 0.000075, 0.0003, '2024-01-01')
ON CONFLICT (provider, model, effective_from) DO NOTHING;

-- Grant permissions (adjust as needed for your setup)
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO your_app_user;
-- GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO your_app_user;

