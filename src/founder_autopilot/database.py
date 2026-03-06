from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
import json
from pathlib import Path
import sqlite3
from typing import Callable, Iterator, Sequence

from importlib.resources import files

from founder_autopilot.adapters import SourceEvent
from founder_autopilot.contracts import ActivityEvent, TrackerConfig
from founder_autopilot.normalization import (
    compute_checksum,
    make_deterministic_id,
    normalize_timestamp,
)


def utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


@dataclass(slots=True)
class PersistedEvents:
    received: int = 0
    raw_inserted: int = 0
    activity_inserted: int = 0
    duplicates: int = 0
    invalid: int = 0
    latest_cursor: str | None = None


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

    def persist_source_events(
        self,
        *,
        project_id: str,
        source: str,
        events: Sequence[SourceEvent],
        normalizer: Callable[..., ActivityEvent],
    ) -> PersistedEvents:
        persisted = PersistedEvents(received=len(events))
        if not events:
            return persisted

        sorted_events = sorted(events, key=lambda event: event.cursor)
        timestamp = utc_now_iso()
        with self.connect() as connection:
            for event in sorted_events:
                observed_at = normalize_timestamp(event.observed_at)
                payload = {
                    **event.payload,
                    "observedAt": observed_at,
                    "sourceEventId": event.source_event_id,
                }
                checksum = compute_checksum(source, payload)
                raw_event_id = make_deterministic_id(
                    "raw",
                    project_id,
                    source,
                    checksum,
                )
                payload_json = json.dumps(
                    payload,
                    sort_keys=True,
                    separators=(",", ":"),
                )
                inserted = connection.execute(
                    """
                    INSERT OR IGNORE INTO raw_events (
                        id,
                        project_id,
                        source,
                        observed_at,
                        cursor_value,
                        checksum,
                        payload_json,
                        created_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                    """,
                    (
                        raw_event_id,
                        project_id,
                        source,
                        observed_at,
                        event.cursor,
                        checksum,
                        payload_json,
                        timestamp,
                    ),
                )
                if inserted.rowcount == 0:
                    persisted.duplicates += 1
                    persisted.latest_cursor = event.cursor
                    continue

                persisted.raw_inserted += 1
                try:
                    activity = normalizer(
                        project_id=project_id,
                        source=source,
                        raw_event_id=raw_event_id,
                        payload=payload,
                    )
                except ValueError as exc:
                    invalid_id = make_deterministic_id(
                        "inv",
                        project_id,
                        source,
                        event.source_event_id,
                        checksum,
                    )
                    connection.execute(
                        """
                        INSERT OR IGNORE INTO invalid_events (
                            id,
                            raw_event_id,
                            project_id,
                            source,
                            source_event_id,
                            error_reason,
                            payload_json,
                            created_at
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                        """,
                        (
                            invalid_id,
                            raw_event_id,
                            project_id,
                            source,
                            event.source_event_id,
                            str(exc),
                            payload_json,
                            timestamp,
                        ),
                    )
                    persisted.invalid += 1
                else:
                    connection.execute(
                        """
                        INSERT INTO activity_events (
                            id,
                            raw_event_id,
                            project_id,
                            source,
                            timestamp,
                            actor,
                            signal_type,
                            summary,
                            metadata_json,
                            created_at
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                        """,
                        (
                            activity.id,
                            raw_event_id,
                            activity.project_id,
                            activity.source,
                            activity.timestamp,
                            activity.actor,
                            activity.signal_type,
                            activity.summary,
                            json.dumps(
                                activity.metadata,
                                sort_keys=True,
                                separators=(",", ":"),
                            ),
                            timestamp,
                        ),
                    )
                    persisted.activity_inserted += 1

                persisted.latest_cursor = event.cursor

            connection.execute(
                """
                INSERT INTO source_cursors (project_id, source, cursor_value, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(project_id, source) DO UPDATE SET
                    cursor_value = excluded.cursor_value,
                    updated_at = excluded.updated_at;
                """,
                (
                    project_id,
                    source,
                    persisted.latest_cursor,
                    timestamp,
                ),
            )
            connection.commit()
        return persisted

    def list_activity_events(self, project_id: str) -> list[ActivityEvent]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    id,
                    project_id,
                    source,
                    timestamp,
                    actor,
                    signal_type,
                    summary,
                    metadata_json
                FROM activity_events
                WHERE project_id = ?
                ORDER BY timestamp ASC, id ASC;
                """,
                (project_id,),
            ).fetchall()
        return [
            ActivityEvent(
                id=row["id"],
                source=row["source"],
                timestamp=row["timestamp"],
                actor=row["actor"],
                project_id=row["project_id"],
                signal_type=row["signal_type"],
                summary=row["summary"],
                metadata=json.loads(row["metadata_json"]),
            )
            for row in rows
        ]

    def list_invalid_events(self, project_id: str) -> list[dict[str, object]]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT source, source_event_id, error_reason, payload_json
                FROM invalid_events
                WHERE project_id = ?
                ORDER BY created_at ASC, id ASC;
                """,
                (project_id,),
            ).fetchall()
        return [
            {
                "source": row["source"],
                "source_event_id": row["source_event_id"],
                "error_reason": row["error_reason"],
                "payload": json.loads(row["payload_json"]),
            }
            for row in rows
        ]

    def table_count(self, table_name: str) -> int:
        if table_name not in {"activity_events", "invalid_events", "raw_events", "source_cursors"}:
            raise ValueError(f"unsupported table count target: {table_name}")
        with self.connect() as connection:
            row = connection.execute(f"SELECT COUNT(*) AS count FROM {table_name};").fetchone()
        return int(row["count"])

    def _load_migrations(self) -> list[tuple[str, str]]:
        migration_dir = files("founder_autopilot").joinpath("migrations")
        migrations: list[tuple[str, str]] = []
        for path in sorted(migration_dir.iterdir(), key=lambda entry: entry.name):
            if path.name.endswith(".sql"):
                migrations.append((path.name, path.read_text(encoding="utf-8")))
        return migrations
