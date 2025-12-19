"""
Billing Reports
===============
Generate CSV billing reports for tenants.
"""

import csv
from datetime import date, datetime
from io import StringIO
from pathlib import Path
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from backend.database import get_session_context
from backend.models.usage import TenantMonthlySummary

logger = structlog.get_logger()


class BillingReportJob:
    """
    Generate billing reports in CSV format.
    """

    def __init__(self, output_dir: str = "reports"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    async def generate_monthly_report(
        self,
        year: int,
        month: int,
        tenant_id: Optional[str] = None,
    ) -> Path:
        """
        Generate monthly billing report.
        
        Args:
            year: Report year
            month: Report month
            tenant_id: Optional specific tenant (all if None)
            
        Returns:
            Path to generated CSV file
        """
        logger.info(
            "Generating monthly billing report",
            year=year,
            month=month,
            tenant_id=tenant_id,
        )

        async with get_session_context() as session:
            stmt = select(TenantMonthlySummary).where(
                TenantMonthlySummary.year == year,
                TenantMonthlySummary.month == month,
            )

            if tenant_id:
                stmt = stmt.where(TenantMonthlySummary.tenant_id == tenant_id)

            stmt = stmt.order_by(
                TenantMonthlySummary.tenant_id,
                TenantMonthlySummary.provider,
                TenantMonthlySummary.model,
            )

            result = await session.execute(stmt)
            rows = result.scalars().all()

            # Generate filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            if tenant_id:
                filename = f"billing_{tenant_id}_{year}_{month:02d}_{timestamp}.csv"
            else:
                filename = f"billing_all_{year}_{month:02d}_{timestamp}.csv"

            output_path = self.output_dir / filename

            # Write CSV
            with open(output_path, "w", newline="") as f:
                writer = csv.writer(f)
                
                # Header
                writer.writerow([
                    "Tenant ID",
                    "Year",
                    "Month",
                    "Provider",
                    "Model",
                    "Total Requests",
                    "Prompt Tokens",
                    "Completion Tokens",
                    "Total Tokens",
                    "Total Cost (USD)",
                ])

                # Data rows
                for row in rows:
                    writer.writerow([
                        row.tenant_id,
                        row.year,
                        row.month,
                        row.provider,
                        row.model,
                        row.total_requests,
                        row.total_prompt_tokens,
                        row.total_completion_tokens,
                        row.total_tokens,
                        f"{row.total_cost:.10f}",
                    ])

                # Summary row if multiple tenants
                if not tenant_id and rows:
                    total_requests = sum(r.total_requests for r in rows)
                    total_tokens = sum(r.total_tokens for r in rows)
                    total_cost = sum(r.total_cost for r in rows)
                    
                    writer.writerow([])
                    writer.writerow([
                        "TOTAL",
                        year,
                        month,
                        "-",
                        "-",
                        total_requests,
                        "-",
                        "-",
                        total_tokens,
                        f"{total_cost:.10f}",
                    ])

            logger.info(
                "Billing report generated",
                path=str(output_path),
                records=len(rows),
            )
            return output_path

    async def generate_tenant_summary_report(
        self,
        tenant_id: str,
        start_year: int,
        start_month: int,
        end_year: int,
        end_month: int,
    ) -> Path:
        """
        Generate a summary report for a tenant across multiple months.
        """
        logger.info(
            "Generating tenant summary report",
            tenant_id=tenant_id,
            period=f"{start_year}-{start_month:02d} to {end_year}-{end_month:02d}",
        )

        async with get_session_context() as session:
            stmt = select(TenantMonthlySummary).where(
                TenantMonthlySummary.tenant_id == tenant_id,
            )

            # Filter by date range
            stmt = stmt.where(
                (TenantMonthlySummary.year > start_year) |
                ((TenantMonthlySummary.year == start_year) & 
                 (TenantMonthlySummary.month >= start_month))
            )
            stmt = stmt.where(
                (TenantMonthlySummary.year < end_year) |
                ((TenantMonthlySummary.year == end_year) & 
                 (TenantMonthlySummary.month <= end_month))
            )

            stmt = stmt.order_by(
                TenantMonthlySummary.year,
                TenantMonthlySummary.month,
                TenantMonthlySummary.provider,
            )

            result = await session.execute(stmt)
            rows = result.scalars().all()

            # Generate filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"summary_{tenant_id}_{start_year}{start_month:02d}_to_{end_year}{end_month:02d}_{timestamp}.csv"
            output_path = self.output_dir / filename

            # Write CSV
            with open(output_path, "w", newline="") as f:
                writer = csv.writer(f)
                
                writer.writerow([
                    "Year",
                    "Month",
                    "Provider",
                    "Model",
                    "Requests",
                    "Tokens",
                    "Cost (USD)",
                ])

                for row in rows:
                    writer.writerow([
                        row.year,
                        row.month,
                        row.provider,
                        row.model,
                        row.total_requests,
                        row.total_tokens,
                        f"{row.total_cost:.10f}",
                    ])

            logger.info(
                "Tenant summary report generated",
                path=str(output_path),
                records=len(rows),
            )
            return output_path

