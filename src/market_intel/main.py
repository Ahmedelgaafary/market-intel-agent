import logging
import os

from langchain_google_genai import ChatGoogleGenerativeAI

from market_intel.application import run_once
from market_intel.config import load_config
from market_intel.scheduler import start_scheduler

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "gemini-3.5-flash-lite"
DEFAULT_MODEL_TIMEOUT = 45


def create_model():
    """Create the configured Gemini model."""

    if not os.getenv("GOOGLE_API_KEY"):
        raise ValueError("GOOGLE_API_KEY is not configured. Add it to your .env file.")

    model_name = os.getenv("GEMINI_MODEL", DEFAULT_MODEL)

    logger.info("Initializing Gemini model: %s", model_name)

    return ChatGoogleGenerativeAI(
        model=model_name,
        timeout=DEFAULT_MODEL_TIMEOUT,
        max_retries=0,
    )


def run_scheduled_agent(*, model=None, config_path="config.yaml") -> None:
    """Start weekly monitoring without an immediate run."""

    config = load_config(config_path)

    if model is None:
        model = create_model()

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

    logger.info("Starting weekly monitoring scheduler.")

    start_scheduler(
        job=monitoring_job,
        schedule=config.schedule,
    )


def main() -> None:
    """Application entry point."""

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    run_scheduled_agent()
