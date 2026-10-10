import logging
import os


def setup_logging():
    """Configure logging once, at the entry point. LOG_LEVEL=DEBUG shows the routine messages."""
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO").upper(),
        format="%(asctime)s %(levelname)-7s %(name)s %(message)s",
    )
