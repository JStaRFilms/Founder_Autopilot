from __future__ import annotations

from contextlib import contextmanager
from datetime import UTC, datetime
import json
from pathlib import Path
import sqlite3
from typing import Iterator

from importlib.resources import files

from founder_autopilot.contracts import TrackerConfig


def utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


class Database:
    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path).expanduser().resolve()

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON;")
        try:
            yield connection
        finally:
            connection.close()

    def initialize(self) -> list[str]:
        with self.connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    name TEXT PRIMARY KEY,
                    applied_at TEXT NOT NULL
                );
                """
            )
            applied = {
                row["name"]
                for row in connection.execute("SELECT name FROM schema_migrations;")
            }
            applied_now: list[str] = []

            for migration_name, migration_sql in self._load_migrations():
                if migration_name in applied:
                    continue
                connection.executescript(migration_sql)
                connection.execute(
                    "INSERT INTO schema_migrations (name, applied_at) VALUES (?, ?);",
                    (migration_name, utc_now_iso()),
                )
                applied_now.append(migration_name)

            connection.commit()
            return applied_now

    def bootstrap_project(self, tracker_config: TrackerConfig) -> None:
        timestamp = utc_now_iso()
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO projects (id, display_name, created_at, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    display_name = excluded.display_name,
                    updated_at = excluded.updated_at;
                """,
                (
                    tracker_config.project_id,
                    tracker_config.project_id.replace("-", " ").title(),
                    timestamp,
                    timestamp,
                ),
            )
            connection.execute(
                """
                INSERT INTO tracker_configs (
                    project_id,
                    config_json,
                    schema_version,
                    updated_at
                )
                VALUES (?, ?, ?, ?)
                ON CONFLICT(project_id) DO UPDATE SET
                    config_json = excluded.config_json,
                    schema_version = excluded.schema_version,
                    updated_at = excluded.updated_at;
                """,
                (
                    tracker_config.project_id,
                    json.dumps(
                        tracker_config.to_contract_dict(),
                        sort_keys=True,
                        separators=(",", ":"),
                    ),
                    1,
                    timestamp,
                ),
            )
            connection.commit()

    def get_source_cursor(self, project_id: str, source: str) -> str | None:
        with self.connect() as connection:
            row = connection.execute(
                """
                SELECT cursor_value
                FROM source_cursors
                WHERE project_id = ? AND source = ?;
                """,
                (project_id, source),
            ).fetchone()
        return None if row is None else row["cursor_value"]

    def _load_migrations(self) -> list[tuple[str, str]]:
        migration_dir = files("founder_autopilot").joinpath("migrations")
        migrations: list[tuple[str, str]] = []
        for path in sorted(migration_dir.iterdir(), key=lambda entry: entry.name):
            if path.name.endswith(".sql"):
                migrations.append((path.name, path.read_text(encoding="utf-8")))
        return migrations
