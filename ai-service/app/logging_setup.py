"""JSON log lines on stdout (docs/02_ARCHITECTURE.md sec. 8, docs/07_SECURITY.md sec. 6).

The start scripts tee stdout into logs\\<service>.log. Context goes in `extra=` (job_id, complaint_id, step,
error_type ...). JSON encoding escapes CR/LF, so user text cannot forge log lines. Never log secrets, tokens,
full phone numbers, personal data or image bytes.
"""

from __future__ import annotations

import datetime as dt
import json
import logging
import sys

CONTEXT_KEYS = (
    "worker_id", "job_id", "job_type", "complaint_id", "run_id", "step", "error_type",
    "attempts", "status", "duration_ms", "count", "request_id",
)


class JsonFormatter(logging.Formatter):
    def __init__(self, service: str) -> None:
        super().__init__()
        self.service = service

    def format(self, record: logging.LogRecord) -> str:
        entry: dict[str, object] = {
            "ts": dt.datetime.fromtimestamp(record.created, dt.UTC).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "service": self.service,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        for key in CONTEXT_KEYS:
            value = getattr(record, key, None)
            if value is not None:
                entry[key] = value
        if record.exc_info:
            entry["exc"] = self.formatException(record.exc_info)
        return json.dumps(entry, ensure_ascii=False, default=str)


def configure_logging(level: str = "INFO", service: str = "worker") -> None:
    """Route the root logger and uvicorn's loggers through one JSON handler on stdout."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter(service))
    root = logging.getLogger()
    root.handlers[:] = [handler]
    root.setLevel(level)
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        lg = logging.getLogger(name)
        lg.handlers[:] = [handler]
        lg.propagate = False
