from pyinline import inline
import logging

log = logging.getLogger(__name__)


@inline
def log_error(msg: str, exception: Exception):
    log.error(msg, exception, exc_info=True)


try:
    x = 1 / 0
except Exception as e:
    log_error("Could not divide number", e)
