import logging
from collections.abc import Callable
from zoneinfo import ZoneInfo

from apscheduler.schedulers.blocking import BlockingScheduler

from market_intel.config import ScheduleConfig

logger = logging.getLogger(__name__)


def start_scheduler(
    *,
    job: Callable[[], object],
    schedule: ScheduleConfig,
) -> None:
    """Run the supplied job according to the configured weekly schedule."""

    scheduler = BlockingScheduler(timezone=ZoneInfo(schedule.timezone))

    def guarded_job() -> None:
        try:
            result = job()
            logger.info("Scheduled workflow finished: %s", result)
        except Exception:
            logger.exception("Scheduled workflow execution failed.")

    weekday = schedule.day[:3].lower()
    scheduler.add_job(
        guarded_job,
        trigger="cron",
        day_of_week=weekday,
        hour=schedule.hour,
        minute=schedule.minute,
        id="weekly_competitor_monitoring",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        misfire_grace_time=3600,
    )

    logger.info(
        "Scheduler started: %s at %02d:%02d (%s)",
        schedule.day,
        schedule.hour,
        schedule.minute,
        schedule.timezone,
    )

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler shutdown requested.")
        scheduler.shutdown(wait=True)
