"""Desktop-only recent-project history backed by Qt settings."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from PySide6.QtCore import QSettings


@dataclass(frozen=True, slots=True)
class RecentProjectEntry:
    """One non-authoritative desktop history record."""

    path: str
    last_opened: str


class RecentProjectsStore:
    """Keep a small deduplicated list without writing scientific project state."""

    _KEY = "v1_1/recent_projects"
    _MAX_STORED = 10

    def __init__(self, settings: QSettings | None = None) -> None:
        self._settings = settings if settings is not None else QSettings("CatalysisWorkbench", "CatalysisWorkbench")

    @staticmethod
    def _normalized(path: str | Path) -> str:
        return str(Path(path).expanduser().resolve(strict=False))

    @staticmethod
    def _dedupe_key(path: str) -> str:
        return os.path.normcase(path)

    def entries(self) -> tuple[RecentProjectEntry, ...]:
        raw = self._settings.value(self._KEY, "[]")
        if not isinstance(raw, str):
            return ()
        try:
            value = json.loads(raw)
        except (TypeError, ValueError):
            return ()
        if not isinstance(value, list):
            return ()
        result: list[RecentProjectEntry] = []
        for item in value:
            if not isinstance(item, dict):
                continue
            path = item.get("path")
            last_opened = item.get("last_opened")
            if not isinstance(path, str) or not path:
                continue
            if not isinstance(last_opened, str) or not last_opened:
                continue
            result.append(RecentProjectEntry(path=path, last_opened=last_opened))
        return tuple(result[: self._MAX_STORED])

    def _write(self, entries: list[RecentProjectEntry]) -> None:
        payload = [
            {"path": entry.path, "last_opened": entry.last_opened}
            for entry in entries[: self._MAX_STORED]
        ]
        self._settings.setValue(
            self._KEY,
            json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
        )
        self._settings.sync()

    def add(self, path: str | Path) -> None:
        normalized = self._normalized(path)
        key = self._dedupe_key(normalized)
        existing = [
            entry for entry in self.entries() if self._dedupe_key(entry.path) != key
        ]
        timestamp = datetime.now(timezone.utc).isoformat()
        self._write([RecentProjectEntry(normalized, timestamp), *existing])

    def remove(self, path: str | Path) -> None:
        normalized = self._normalized(path)
        key = self._dedupe_key(normalized)
        self._write(
            [entry for entry in self.entries() if self._dedupe_key(entry.path) != key]
        )


__all__ = ["RecentProjectEntry", "RecentProjectsStore"]
