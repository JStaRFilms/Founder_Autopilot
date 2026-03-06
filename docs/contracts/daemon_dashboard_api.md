# Daemon Dashboard Contract

## Purpose
This document defines the transport-agnostic contract between the local Python daemon and the future Next.js dashboard. The scaffold in this phase does not ship a full API server yet; it establishes the canonical JSON payloads and SQLite-backed resource model that a local HTTP or IPC layer can expose later without changing payload shapes.

The code source of truth for these payloads lives in `src/founder_autopilot/contracts.py`, and the persistence source of truth lives in `src/founder_autopilot/migrations/0001_initial_schema.sql`.

## Contract Rules
- Payload field names exposed to the dashboard use the camelCase shapes defined in `docs/Project_Requirements.md`.
- Timestamps are ISO-8601 strings in UTC unless a field explicitly carries a timezone.
- Collection payloads are append-only and cursor-friendly so the dashboard can poll without mutating data.
- The transport is local-only in v1. No cloud or remote synchronization is part of this contract.

## Resource Shapes

### `ActivityEvent`
```json
{
  "id": "evt_123",
  "source": "git",
  "timestamp": "2026-03-06T12:00:00+00:00",
  "actor": "founder",
  "projectId": "founder-autopilot",
  "signalType": "code",
  "summary": "Committed daemon bootstrap",
  "metadata": {
    "branch": "main",
    "linesChanged": 42
  }
}
```

### `ProjectSignal`
```json
{
  "id": "sig_123",
  "projectId": "founder-autopilot",
  "windowStart": "2026-03-06T09:00:00+00:00",
  "windowEnd": "2026-03-06T10:00:00+00:00",
  "focusMinutes": 44,
  "driftMinutes": 8,
  "contextSwitchCount": 2,
  "confidence": 0.83,
  "derivedFromEventIds": ["evt_123", "evt_124"]
}
```

### `FocusScore`
```json
{
  "id": "score_2026-03-06",
  "projectId": "founder-autopilot",
  "date": "2026-03-06",
  "score": 78,
  "trend": "up",
  "contributingSignals": [
    {
      "signal": "code",
      "weight": 1,
      "impact": 24
    }
  ],
  "computedAt": "2026-03-06T12:05:00+00:00"
}
```

### `Nudge`
```json
{
  "id": "nudge_123",
  "createdAt": "2026-03-06T12:10:00+00:00",
  "type": "focus",
  "severity": "medium",
  "title": "Return to the main thread",
  "message": "You have switched contexts three times in the last hour.",
  "reason": "High context switching without a completed focus block.",
  "targetChannels": ["codex", "dashboard"],
  "status": "pending"
}
```

### `CycleReport`
```json
{
  "id": "report_2026_w10",
  "projectId": "founder-autopilot",
  "periodStart": "2026-03-02T00:00:00+00:00",
  "periodEnd": "2026-03-08T00:00:00+00:00",
  "averageFocusScore": 74.5,
  "topWins": ["Shipped backend scaffold"],
  "driftPatterns": ["Research sessions ran longer than planned"],
  "recommendedActions": ["Timebox exploratory work to 30 minutes"],
  "generatedAt": "2026-03-08T08:00:00+00:00"
}
```

### `TrackerConfig`
```json
{
  "projectId": "founder-autopilot",
  "watchPaths": [
    "C:/CreativeOS/01_Projects/Code/Personal_Stuff/2026-03-06_Founder_Autopilot/docs",
    "C:/CreativeOS/01_Projects/Code/Personal_Stuff/2026-03-06_Founder_Autopilot/src"
  ],
  "excludedPaths": [
    "C:/CreativeOS/01_Projects/Code/Personal_Stuff/2026-03-06_Founder_Autopilot/.git"
  ],
  "signalWeights": {
    "code": 1,
    "writing": 0.8
  },
  "quietHours": {
    "start": "22:00",
    "end": "07:00",
    "timezone": "Africa/Lagos"
  },
  "nudgeSensitivity": "medium",
  "notificationChannels": ["codex", "dashboard", "os"]
}
```

## Planned Local Endpoints
These are the resource boundaries the dashboard can rely on once a local transport adapter is added:

| Method | Path | Response |
|---|---|---|
| `GET` | `/health` | `{ "status": "ok", "projectId": "...", "lastCycleAt": "..." }` |
| `GET` | `/api/config` | `TrackerConfig` |
| `GET` | `/api/events?limit=100&cursor=<iso>` | `{ "items": ActivityEvent[], "nextCursor": "<iso|null>" }` |
| `GET` | `/api/signals?from=<iso>&to=<iso>` | `{ "items": ProjectSignal[] }` |
| `GET` | `/api/focus-scores/:date` | `FocusScore` |
| `GET` | `/api/nudges?status=pending` | `{ "items": Nudge[] }` |
| `GET` | `/api/reports/latest` | `CycleReport` |

## SQLite Mapping
- `tracker_configs.config_json` stores the canonical `TrackerConfig` payload.
- `raw_events` stores source-specific event payloads before normalization.
- `activity_events` stores canonical `ActivityEvent` rows.
- `invalid_events` quarantines normalization failures with a reason string.
- `project_signals`, `focus_scores`, `nudges`, and `cycle_reports` persist the downstream resources the dashboard will read.
- `source_cursors` stores resumable per-source cursors for daemon polling state.

## Out of Scope For This Phase
- Running a production API server.
- WebSocket streaming.
- Authentication or multi-user concerns.
- Remote sync or any non-local transport.
