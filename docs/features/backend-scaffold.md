# Backend Scaffold

## Overview
This phase establishes the local Python daemon skeleton, SQLite schema, migration runner, and validated config loader for Founder Autopilot v1. It is intentionally narrow: the daemon boots, the database initializes from SQL migrations, and the dashboard-facing contract is fixed without implementing ingestion adapters or scoring logic yet.

## Files
- `pyproject.toml`: package metadata and CLI entrypoint.
- `src/founder_autopilot/cli.py`: `validate-config`, `init-db`, and `run-daemon` commands.
- `src/founder_autopilot/config.py`: TOML loading, path resolution, and validation.
- `src/founder_autopilot/database.py`: SQLite connection and migration/bootstrap flow.
- `src/founder_autopilot/daemon.py`: daemon skeleton with placeholder adapters.
- `src/founder_autopilot/migrations/0001_initial_schema.sql`: base schema for raw events, canonical events, scores, nudges, reports, config, and cursors.
- `docs/contracts/daemon_dashboard_api.md`: transport-agnostic contract for dashboard integration.

## How To Run
Use a local Python 3.11 environment and point the module path at `src`.

```powershell
$env:PYTHONPATH = "src"
python -m founder_autopilot validate-config --config config/tracker.sample.toml
python -m founder_autopilot init-db --config config/tracker.sample.toml
python -m founder_autopilot run-daemon --config config/tracker.sample.toml --once
python -m unittest discover -s tests
```

## Scope Guardrails
- No cloud services, remote APIs, or telemetry.
- No real ingestion adapters yet; only the daemon shell and resumable cursor model.
- No dashboard API server yet; only stable payload definitions and database-backed resources.
