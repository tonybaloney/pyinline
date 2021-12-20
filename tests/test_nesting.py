from pyinline import inline
import logging

log = logging.getLogger(__name__)


@inline
def log_error(msg: str, exception: Exception):
    if len(msg) > 10:
        log.error(msg[:9], exception, exc_info=True)
    else:
        log.error(msg, exception, exc_info=True)


try:
    x = 1 / 0
except Exception as e:
    log_error("Could not divide number", e)
