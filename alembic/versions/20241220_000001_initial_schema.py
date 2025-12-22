"""Initial schema

Revision ID: 20241220_000001
Revises:
Create Date: 2024-12-20 00:00:01

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20241220_000001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Create token_usage_raw table
    op.create_table(
        "token_usage_raw",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", sa.String(255), nullable=False),
        sa.Column("provider", sa.String(50), nullable=False),
        sa.Column("model", sa.String(255), nullable=False),
        sa.Column("prompt_tokens", sa.BigInteger(), nullable=False),
        sa.Column("completion_tokens", sa.BigInteger(), nullable=False),
        sa.Column("total_tokens", sa.BigInteger(), nullable=False),
        sa.Column("calculated_cost", sa.Numeric(20, 10), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("latency_ms", sa.BigInteger(), nullable=True),
        sa.Column("cloud_provider", sa.String(50), nullable=False, server_default="unknown"),
        sa.Column("hostname", sa.String(255), nullable=True),
        sa.Column("instance_id", sa.String(255), nullable=True),
        sa.Column("k8s_pod", sa.String(255), nullable=True),
        sa.Column("k8s_namespace", sa.String(255), nullable=True),
        sa.Column("k8s_node", sa.String(255), nullable=True),
        sa.Column("metadata_json", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes for token_usage_raw
    op.create_index("idx_usage_tenant_id", "token_usage_raw", ["tenant_id"])
    op.create_index("idx_usage_provider", "token_usage_raw", ["provider"])
    op.create_index("idx_usage_model", "token_usage_raw", ["model"])
    op.create_index("idx_usage_timestamp", "token_usage_raw", ["timestamp"])
    op.create_index("idx_usage_tenant_timestamp", "token_usage_raw", ["tenant_id", "timestamp"])
    op.create_index("idx_usage_provider_model", "token_usage_raw", ["provider", "model"])
    op.create_index(
        "idx_usage_cloud_instance", "token_usage_raw", ["cloud_provider", "instance_id"]
    )
    op.create_index("idx_usage_k8s", "token_usage_raw", ["k8s_namespace", "k8s_pod"])

    # Create tenant_daily_summary table
    op.create_table(
        "tenant_daily_summary",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", sa.String(255), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("provider", sa.String(50), nullable=False),
        sa.Column("model", sa.String(255), nullable=False),
        sa.Column("cloud_provider", sa.String(50), nullable=False),
        sa.Column("total_requests", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("total_prompt_tokens", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("total_completion_tokens", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("total_tokens", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("total_cost", sa.Numeric(20, 10), nullable=False, server_default="0"),
        sa.Column("avg_latency_ms", sa.BigInteger(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id", "date", "provider", "model", "cloud_provider", name="uq_daily_summary"
        ),
    )

    # Create indexes for tenant_daily_summary
    op.create_index("idx_daily_tenant_date", "tenant_daily_summary", ["tenant_id", "date"])

    # Create tenant_monthly_summary table
    op.create_table(
        "tenant_monthly_summary",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", sa.String(255), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("month", sa.Integer(), nullable=False),
        sa.Column("provider", sa.String(50), nullable=False),
        sa.Column("model", sa.String(255), nullable=False),
        sa.Column("total_requests", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("total_prompt_tokens", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("total_completion_tokens", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("total_tokens", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("total_cost", sa.Numeric(20, 10), nullable=False, server_default="0"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id", "year", "month", "provider", "model", name="uq_monthly_summary"
        ),
    )

    # Create indexes for tenant_monthly_summary
    op.create_index(
        "idx_monthly_tenant_period", "tenant_monthly_summary", ["tenant_id", "year", "month"]
    )

    # Create pricing_table
    op.create_table(
        "pricing_table",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider", sa.String(50), nullable=False),
        sa.Column("model", sa.String(255), nullable=False),
        sa.Column("input_price_per_1k", sa.Numeric(20, 10), nullable=False),
        sa.Column("output_price_per_1k", sa.Numeric(20, 10), nullable=False),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("effective_to", sa.Date(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider", "model", "effective_from", name="uq_pricing_model_date"),
    )

    # Create indexes for pricing_table
    op.create_index("idx_pricing_lookup", "pricing_table", ["provider", "model", "is_active"])


def downgrade() -> None:
    op.drop_table("pricing_table")
    op.drop_table("tenant_monthly_summary")
    op.drop_table("tenant_daily_summary")
    op.drop_table("token_usage_raw")
