"""Journal of every AI request: one JSON object per line (JSON Lines).

Each line holds the prompt, the answer or the error, the provider and model, time and tokens.
The file contains users' questions, so it stays out of git (logs/ is in .gitignore).
"""

import json
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Protocol


class RequestLog(Protocol):
    def write(self, record: dict[str, Any]) -> None: ...

    def close(self) -> None: ...


class JsonlRequestLog:
    """Appends records to a file; at max_bytes the file is rotated (ai_requests.jsonl.1, ...)."""

    def __init__(self, path: Path, *, max_bytes: int = 10_000_000, backup_count: int = 5) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self._handler = RotatingFileHandler(
            path, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8"
        )
        self._handler.setFormatter(logging.Formatter("%(message)s"))
        # A logger of its own, so these lines never reach the console or other handlers.
        self._logger = logging.getLogger(f"{__name__}.{path.resolve()}")
        self._logger.handlers = [self._handler]
        self._logger.setLevel(logging.INFO)
        self._logger.propagate = False

    def write(self, record: dict[str, Any]) -> None:
        self._logger.info(json.dumps(record, ensure_ascii=False))

    def close(self) -> None:
        self._logger.removeHandler(self._handler)
        self._handler.close()
