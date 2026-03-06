from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from founder_autopilot.analytics import AnalyticsService
from founder_autopilot.config import load_app_config, override_database_path
from founder_autopilot.database import Database
from founder_autopilot.ingestion import IngestionWorker
from founder_autopilot.normalization import build_cursor
from founder_autopilot.scheduler import CadenceScheduler
from founder_autopilot.adapters import SourceEvent


SAMPLE_CONFIG = REPO_ROOT / "config" / "tracker.sample.toml"


class ScoringSchedulerReportTests(unittest.TestCase):
    def test_scheduler_defaults_and_overrides_are_supported(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "tracker.toml"
            config_path.write_text(
                "\n".join(
                    [
                        'project_id = "founder-autopilot"',
                        f'watch_paths = ["{REPO_ROOT.as_posix()}/src"]',
                        f'excluded_paths = ["{REPO_ROOT.as_posix()}/.git"]',
                        'nudge_sensitivity = "medium"',
                        "",
                        "[signal_weights]",
                        "code = 1.0",
                        "writing = 0.8",
                        "planning = 0.7",
                        "research = 0.5",
                        "ops = 0.4",
                        "unknown = 0.2",
                        "",
                        "[quiet_hours]",
                        'start = "22:00"',
                        'end = "07:00"',
                        'timezone = "Africa/Lagos"',
                        "",
                        "[notifications]",
                        "codex = true",
                        "dashboard = true",
                        "os = true",
                        "",
                        "[daemon]",
                        'database_path = "./founder_autopilot.db"',
                        "poll_interval_seconds = 300",
                        'log_level = "INFO"',
                        "",
                        "[scheduler]",
                        'summary_times = ["08:00", "12:30", "18:30"]',
                        "cycle_length_days = 7",
                        'cycle_anchor_date = "2026-03-03"',
                    ]
                ),
                encoding="utf-8",
            )

            config = load_app_config(config_path)
            scheduler = CadenceScheduler(config.scheduler)
            summary_window = scheduler.current_summary_window("2026-03-06T12:45:00+01:00")
            cycle_window = scheduler.cycle_window_for("2026-03-06T12:45:00+01:00")

            self.assertEqual(config.scheduler.summary_times, ["08:00", "12:30", "18:30"])
            self.assertEqual(config.scheduler.cycle_length_days, 7)
            self.assertEqual(summary_window.window_start, "2026-03-06T07:00:00+00:00")
            self.assertEqual(summary_window.window_end, "2026-03-06T11:30:00+00:00")
            self.assertEqual(cycle_window.start, "2026-03-02T23:00:00+00:00")
            self.assertEqual(cycle_window.end, "2026-03-09T23:00:00+00:00")

    def test_analytics_refresh_persists_scores_and_generates_reports(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database_path = Path(temp_dir) / "analytics.db"
            database = Database(database_path)
            database.initialize()
            config = override_database_path(load_app_config(SAMPLE_CONFIG), database_path)
            database.bootstrap_project(config.tracker)
            worker = IngestionWorker(database, config.tracker.project_id)

            worker.ingest(
                "cos",
                [
                    self._cos_event(
                        "evt-1",
                        "2026-03-02T09:10:00+01:00",
                        "Implemented scoring engine",
                        "code",
                    ),
                    self._cos_event(
                        "evt-2",
                        "2026-03-02T10:00:00+01:00",
                        "Drafted reporting notes",
                        "writing",
                    ),
                    self._cos_event(
                        "evt-3",
                        "2026-03-03T11:15:00+01:00",
                        "Researched notification APIs",
                        "research",
                    ),
                    self._cos_event(
                        "evt-4",
                        "2026-03-03T12:05:00+01:00",
                        "Adjusted daemon config",
                        "ops",
                    ),
                    self._cos_event(
                        "evt-5",
                        "2026-03-06T09:20:00+01:00",
                        "Built report generation module",
                        "code",
                    ),
                    self._cos_event(
                        "evt-6",
                        "2026-03-06T10:10:00+01:00",
                        "Outlined next actions",
                        "planning",
                    ),
                ],
            )

            analytics = AnalyticsService(database, config)
            first_snapshot = analytics.refresh(as_of="2026-03-06T13:05:00+01:00")
            second_snapshot = analytics.refresh(as_of="2026-03-06T13:05:00+01:00")

            self.assertEqual(len(first_snapshot.daily_scorecards), 3)
            self.assertEqual(database.table_count("project_signals"), 3)
            self.assertEqual(database.table_count("focus_scores"), 3)
            self.assertEqual(database.table_count("cycle_reports"), 1)
            self.assertIsNotNone(first_snapshot.daily_report)
            self.assertIsNotNone(first_snapshot.cycle_report)
            self.assertEqual(
                first_snapshot.daily_report.window_start,
                "2026-03-06T08:00:00+00:00",
            )
            self.assertEqual(
                first_snapshot.daily_report.window_end,
                "2026-03-06T12:00:00+00:00",
            )
            self.assertGreater(first_snapshot.daily_report.focus_score, 0)
            self.assertTrue(first_snapshot.daily_report.top_wins)
            self.assertTrue(first_snapshot.daily_report.recommended_actions)
            self.assertGreater(first_snapshot.cycle_report.average_focus_score, 0)
            self.assertTrue(first_snapshot.cycle_report.top_wins)
            self.assertTrue(first_snapshot.cycle_report.drift_patterns)
            self.assertTrue(first_snapshot.cycle_report.recommended_actions)
            self.assertEqual(
                [card.focus_score.score for card in first_snapshot.daily_scorecards],
                [card.focus_score.score for card in second_snapshot.daily_scorecards],
            )
            self.assertEqual(database.table_count("cycle_reports"), 1)

    def _cos_event(
        self,
        source_event_id: str,
        timestamp: str,
        summary: str,
        signal_type: str,
    ) -> SourceEvent:
        return SourceEvent(
            source_event_id=source_event_id,
            observed_at=timestamp,
            cursor=build_cursor(timestamp, source_event_id),
            payload={
                "id": source_event_id,
                "timestamp": timestamp,
                "summary": summary,
                "signalType": signal_type,
            },
        )


if __name__ == "__main__":
    unittest.main()
