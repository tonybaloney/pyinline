from pyinline import inline
import logging

log = logging.getLogger(__name__)


@inline
def log_error():
    log.error("There has been an error!")


log_error()
