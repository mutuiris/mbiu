"""Configure pipeline logging with the sanitizing log filter."""

import logging
from typing import TextIO

from mbiu.security.logging import SanitizedLogFilter

PIPELINE_LOGGER = "mbiu.pipeline"


def configure_pipeline_logging(
    level: int = logging.INFO,
    *,
    logger: logging.Logger | None = None,
    stream: TextIO | None = None,
    sanitized_filter: logging.Filter | None = None,
) -> logging.Logger:
    """Attach one sanitized stream handler to the pipeline logger.

    Child loggers such as ``mbiu.pipeline.fetch`` propagate here, so every pipeline
    record passes through the ``SanitizedLogFilter``.

    Args:
        level: Minimum level for the pipeline logger.
        logger: Optional logger override, mainly for tests.
        stream: Optional output stream, mainly for tests.
        sanitized_filter: Optional filter override; defaults to the sanitizing filter.

    Returns:
        The configured logger.
    """
    target = logger or logging.getLogger(PIPELINE_LOGGER)
    target.setLevel(level)
    target.propagate = False
    for handler in list(target.handlers):
        target.removeHandler(handler)

    handler = logging.StreamHandler(stream)
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
    handler.addFilter(sanitized_filter or SanitizedLogFilter())
    target.addHandler(handler)
    return target
