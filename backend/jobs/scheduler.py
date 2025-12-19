"""
Job Scheduler
=============
APScheduler-based job scheduler for aggregation and reporting.
"""

import asyncio
from datetime import date, datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import structlog

from backend.config import settings
from backend.jobs.aggregation import DailyAggregationJob, MonthlyAggregationJob
from backend.jobs.reports import BillingReportJob

logger = structlog.get_logger()


class JobScheduler:
    """
    Manages scheduled background jobs.
    """

    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.daily_job = DailyAggregationJob()
        self.monthly_job = MonthlyAggregationJob()
        self.report_job = BillingReportJob()

    async def run_daily_aggregation(self) -> None:
        """Execute daily aggregation job."""
        try:
            logger.info("Running scheduled daily aggregation")
            count = await self.daily_job.run()
            logger.info("Daily aggregation completed", records=count)
        except Exception as e:
            logger.error("Daily aggregation failed", error=str(e))

    async def run_monthly_aggregation(self) -> None:
        """Execute monthly aggregation job."""
        try:
            logger.info("Running scheduled monthly aggregation")
            count = await self.monthly_job.run()
            logger.info("Monthly aggregation completed", records=count)
        except Exception as e:
            logger.error("Monthly aggregation failed", error=str(e))

    async def run_monthly_reports(self) -> None:
        """Generate monthly billing reports."""
        try:
            # Get previous month
            today = date.today()
            if today.month == 1:
                year, month = today.year - 1, 12
            else:
                year, month = today.year, today.month - 1

            logger.info("Generating monthly billing reports", year=year, month=month)
            path = await self.report_job.generate_monthly_report(year, month)
            logger.info("Monthly reports generated", path=str(path))
        except Exception as e:
            logger.error("Monthly report generation failed", error=str(e))

    def setup(self) -> None:
        """Configure scheduled jobs."""
        # Daily aggregation - runs at configured hour (default 2 AM)
        self.scheduler.add_job(
            self.run_daily_aggregation,
            CronTrigger(hour=settings.daily_aggregation_hour, minute=0),
            id="daily_aggregation",
            name="Daily Token Aggregation",
            replace_existing=True,
        )

        # Monthly aggregation - runs on configured day (default 1st) at 3 AM
        self.scheduler.add_job(
            self.run_monthly_aggregation,
            CronTrigger(
                day=settings.monthly_aggregation_day,
                hour=3,
                minute=0,
            ),
            id="monthly_aggregation",
            name="Monthly Token Aggregation",
            replace_existing=True,
        )

        # Monthly reports - runs on 2nd of month at 4 AM
        self.scheduler.add_job(
            self.run_monthly_reports,
            CronTrigger(day=2, hour=4, minute=0),
            id="monthly_reports",
            name="Monthly Billing Reports",
            replace_existing=True,
        )

        logger.info(
            "Scheduler configured",
            daily_hour=settings.daily_aggregation_hour,
            monthly_day=settings.monthly_aggregation_day,
        )

    def start(self) -> None:
        """Start the scheduler."""
        self.scheduler.start()
        logger.info("Scheduler started")

    def stop(self) -> None:
        """Stop the scheduler."""
        self.scheduler.shutdown()
        logger.info("Scheduler stopped")


async def run_scheduler() -> None:
    """Run the job scheduler."""
    scheduler = JobScheduler()
    scheduler.setup()
    scheduler.start()

    try:
        # Keep the scheduler running
        while True:
            await asyncio.sleep(60)
    except (KeyboardInterrupt, SystemExit):
        scheduler.stop()


def run() -> None:
    """Entry point for the scheduler worker."""
    if not settings.scheduler_enabled:
        logger.warning("Scheduler is disabled")
        return

    logger.info("Starting Token Trackr Scheduler")
    asyncio.run(run_scheduler())


if __name__ == "__main__":
    run()

