"""Structured JSON logging — works locally and on any cloud."""
import json, logging, sys
from datetime import datetime, timezone


class JsonFormatter(logging.Formatter):
    LEVELS = {logging.DEBUG:"DEBUG", logging.INFO:"INFO",
               logging.WARNING:"WARNING", logging.ERROR:"ERROR", logging.CRITICAL:"CRITICAL"}

    def format(self, record: logging.LogRecord) -> str:
        skip = {"name","msg","args","levelname","levelno","pathname","filename","module",
                "exc_info","exc_text","stack_info","lineno","funcName","created","msecs",
                "relativeCreated","thread","threadName","processName","process","message"}
        entry = {
            "level":     self.LEVELS.get(record.levelno, "DEFAULT"),
            "message":   record.getMessage(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "module":    record.module,
            "function":  record.funcName,
        }
        if record.exc_info:
            entry["exception"] = self.formatException(record.exc_info)
        entry.update({k: v for k, v in record.__dict__.items() if k not in skip})
        return json.dumps(entry, default=str)


def setup_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))
    root.handlers = [handler]
    for noisy in ("uvicorn.access", "sqlalchemy.engine"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
