from __future__ import annotations

from dataclasses import dataclass

from founder_autopilot.adapters import SourceEvent
from founder_autopilot.database import Database, PersistedEvents
from founder_autopilot.normalization import normalize_activity_event


@dataclass(slots=True)
class IngestionWorker:
    database: Database
    project_id: str

    def ingest(self, source: str, events: list[SourceEvent]) -> PersistedEvents:
        return self.database.persist_source_events(
            project_id=self.project_id,
            source=source,
            events=events,
            normalizer=normalize_activity_event,
        )
