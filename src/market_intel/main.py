import logging

from market_intel.application import run_once
from market_intel.config import load_config
from market_intel.scheduler import start_scheduler

logger = logging.getLogger(__name__)


def run_scheduled_agent(*, model, config_path="config.yaml") -> None:
    """Load configuration and start weekly monitoring."""

    config = load_config(config_path)

    def monitoring_job():
        logger.info("Starting scheduled competitor monitoring.")

        result = run_once(
            config=config,
            model=model,
        )

        logger.info(
            "Monitoring run %s finished with status %s.",
            result.get("run_id"),
            result.get("status"),
        )

        return result

    start_scheduler(
        job=monitoring_job,
        schedule=config.schedule,
    )
