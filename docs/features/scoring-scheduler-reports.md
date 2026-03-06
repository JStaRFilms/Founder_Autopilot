# Scoring, Scheduler, and Reports

## Overview
This feature layer turns normalized `activity_events` into deterministic daily focus scores, scheduled daily summaries, and rolling two-week cycle reports. The implementation stays local-first and explainable: every score is derived from stored event windows, every report section is generated from persisted score inputs, and cycle reports are saved back to SQLite for later dashboard use.

## Architecture
- `src/founder_autopilot/scoring.py`: builds window assessments, daily `ProjectSignal` rows, and persisted `FocusScore` records.
- `src/founder_autopilot/scheduler.py`: resolves the default 3x-daily cadence, supports config overrides, and computes active two-week cycle windows.
- `src/founder_autopilot/reporting.py`: creates scheduled daily summary payloads and persisted `CycleReport` artifacts.
- `src/founder_autopilot/analytics.py`: orchestrates recomputation from SQLite-backed `ActivityEvent` rows and writes score/report outputs through the database layer.
- `src/founder_autopilot/database.py`: upserts `project_signals`, `focus_scores`, and `cycle_reports`.
- `src/founder_autopilot/cli.py`: exposes `generate-reports` to recompute analytics on demand.

## Scoring Model
- Focus minutes come from `code`, `writing`, and `planning` events.
- Drift minutes come from `research`, `ops`, and `unknown` events.
- Event durations are inferred from gaps between chronological events with bounded per-event minutes so long idle gaps do not inflate scores.
- Momentum, drift, and overload are derived from focus minutes, drift minutes, context switches, and work-block length.
- Daily focus scores remain idempotent because signal IDs and score IDs are deterministic for the same project/date window.

## Scheduling
- Default daily summary cadence is `09:00`, `13:00`, and `17:00` in the configured scheduler timezone.
- Optional `[scheduler]` config overrides support custom summary times, a custom cycle length, and a cycle anchor date.
- The sample config anchors the default two-week cycle on `2026-03-02`, producing deterministic windows from that date onward.

## Reports
- Daily reports contain a window summary plus top wins, drift risks, and recommended next actions.
- Cycle reports contain average focus score, top wins, drift patterns, and recommended actions for the active cycle window.
- Only cycle reports are persisted in SQLite for now; daily reports are generated on demand from the current scheduled window.

## Verification
- `python -m pytest -q`
- `python -m unittest discover -s tests -v`
