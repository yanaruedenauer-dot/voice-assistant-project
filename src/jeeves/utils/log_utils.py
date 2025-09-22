# src/jeeves/utils/log_utils.py
import re
import logging
from logging import Logger

REDACT: re.Pattern[str] = re.compile(r"(api_key|token|authorization)=([^&\s]+)", re.I)


def redact(s: str) -> str:
    return REDACT.sub(r"\1=***", s)


logger: Logger = logging.getLogger("jeeves")
