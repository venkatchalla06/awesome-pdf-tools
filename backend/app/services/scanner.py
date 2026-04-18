import logging
import clamd
from app.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


def scan_file(file_path: str) -> tuple[bool, str | None]:
    """
    Returns (is_clean, threat_name).
    Fails open if ClamAV is unavailable (log + alert in production).
    """
    try:
        cd = clamd.ClamdNetworkSocket(
            host=settings.CLAMAV_HOST,
            port=settings.CLAMAV_PORT,
            timeout=30,
        )
        result = cd.scan(file_path)
        if result is None:
            return True, None
        status, threat = result.get(file_path, ("OK", None))
        return status == "OK", threat
    except Exception as e:
        logger.warning("ClamAV unavailable: %s — skipping scan", e)
        return True, None  # Fail open; swap to False for stricter policy
