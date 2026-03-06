from __future__ import annotations

from pathlib import Path
import time

from founder_autopilot.adapters import Adapter, COSAdapter, FileSystemAdapter, GitAdapter
from founder_autopilot.config import load_app_config, override_database_path
from founder_autopilot.database import Database
from founder_autopilot.ingestion import IngestionWorker


class DaemonService:
    def __init__(
        self,
        config_path: str | Path,
        *,
        database_path: str | Path | None = None,
        adapters: list[Adapter] | None = None,
    ) -> None:
        self.config_path = Path(config_path).expanduser().resolve()
        config = load_app_config(self.config_path)
        if database_path is not None:
            config = override_database_path(config, database_path)

        self.config = config
        self.database = Database(config.daemon.database_path)
        self.ingestion = IngestionWorker(self.database, config.tracker.project_id)
        self.adapters = adapters or self._build_default_adapters()

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
            events = adapter.collect(cursor)
            persisted = self.ingestion.ingest(adapter.name, events)
            counts[adapter.name] = persisted.activity_inserted
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

    def _build_default_adapters(self) -> list[Adapter]:
        project_root = self.config_path.parent.parent
        cos_root = project_root / "data" / "cos"
        return [
            GitAdapter(self.config.tracker.watch_paths),
            COSAdapter([str(cos_root)]),
            FileSystemAdapter(
                self.config.tracker.watch_paths,
                self.config.tracker.excluded_paths,
            ),
        ]
