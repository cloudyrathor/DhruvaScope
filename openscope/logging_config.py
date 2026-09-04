import logging


def configure_logging(level: int = logging.INFO) -> logging.Logger:
    """Configure and return the root OpenScope logger."""
    logger = logging.getLogger("openscope")
    logger.setLevel(level)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
        logger.addHandler(handler)
    return logger
