# Pyinline

A function inliner for Python. Import `inline` from `pyinline` and run:

```console
$ python -m pyinline source.py
```

This will convert the following:

```python
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

```

will generate:

```python
import logging

log = logging.getLogger(__name__)


try:
    x = 1 / 0
except Exception as e:
    log.error("Could not divide number", e, exc_info=True)
```

Call with `--diff` to generate a patch.