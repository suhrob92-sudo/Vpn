"""Structured logging with secret redaction."""
import logging
import re
import sys

# Values matching these patterns are masked in log output so tokens/passwords
# never leak even when third-party libs log request details.
_SECRET_PATTERNS = [
    re.compile(r"(\d{6,}:[A-Za-z0-9_-]{30,})"),          # telegram bot tokens
    re.compile(r"(Crypto-Pay-API-Token['\":= ]+)([^\s'\"]+)", re.I),
    re.compile(r"(password['\":= ]+)([^\s'\",}]+)", re.I),
    re.compile(r"(authorization['\":= ]+)([^\s'\"]+)", re.I),
]


class RedactingFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage()
        redacted = msg
        for pat in _SECRET_PATTERNS:
            redacted = pat.sub(
                lambda m: (m.group(1) if m.lastindex and m.lastindex > 1 else "") + "***",
                redacted,
            )
        if redacted != msg:
            record.msg = redacted
            record.args = ()
        return True


def setup_logging(level: int = logging.INFO) -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    )
    handler.addFilter(RedactingFilter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
