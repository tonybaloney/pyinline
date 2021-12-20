from pyinline import inline
import logging

log = logging.getLogger(__name__)


@inline
def log_error(msg: str, exception: Exception):
    log.error(msg, exception, exc_info=True)
    if len(msg) > 10:
        log_error(msg[:9], exception)


try:
    x = 1 / 0
except Exception as e:
    log_error("Could not divide number", e)
