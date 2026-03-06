from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import time
from typing import Protocol

from founder_autopilot.config import load_app_config, override_database_path
from founder_autopilot.database import Database


class Adapter(Protocol):
    name: str

    def collect(self, since: str | None) -> list[dict[str, object]]:
        ...


@dataclass(slots=True)
class NoopAdapter:
    name: str

    def collect(self, since: str | None) -> list[dict[str, object]]:
        _ = since
        return []


class DaemonService:
    def __init__(
        self,
        config_path: str | Path,
        *,
        database_path: str | Path | None = None,
        adapters: list[Adapter] | None = None,
    ) -> None:
        config = load_app_config(config_path)
        if database_path is not None:
            config = override_database_path(config, database_path)

        self.config = config
        self.database = Database(config.daemon.database_path)
        self.adapters = adapters or [
            NoopAdapter("git"),
            NoopAdapter("cos"),
            NoopAdapter("filesystem"),
        ]

    def bootstrap(self) -> list[str]:
        applied = self.database.initialize()
        self.database.bootstrap_project(self.config.tracker)
        return applied

    def run_cycle(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for adapter in self.adapters:
            cursor = self.database.get_source_cursor(
                self.config.tracker.project_id,
                adapter.name,
            )
            counts[adapter.name] = len(adapter.collect(cursor))
        return counts

    def run(self, *, once: bool = False) -> None:
        applied = self.bootstrap()
        cycle = 1
        while True:
            counts = self.run_cycle()
            migration_text = ", ".join(applied) if applied else "none"
            source_text = ", ".join(
                f"{name}={count}" for name, count in counts.items()
            )
            print(
                "Founder Autopilot daemon cycle "
                f"{cycle} | migrations={migration_text} | events={source_text}"
            )
            if once:
                return
            cycle += 1
            time.sleep(self.config.daemon.poll_interval_seconds)
