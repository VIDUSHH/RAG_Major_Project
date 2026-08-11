import logging
import sys
from app.core.config import settings

def setup_logging() -> None:
    """Configures application-wide logging format and severity level."""
    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)]
    )

logger = logging.getLogger("fastapi_backend")
