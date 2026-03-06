from __future__ import annotations

from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from founder_autopilot.adapters import COSAdapter, FileSystemAdapter, GitAdapter, SourceEvent
from founder_autopilot.config import load_app_config, override_database_path
from founder_autopilot.daemon import DaemonService
from founder_autopilot.database import Database
from founder_autopilot.ingestion import IngestionWorker
from founder_autopilot.normalization import build_cursor


SAMPLE_CONFIG = REPO_ROOT / "config" / "tracker.sample.toml"


class BackendScaffoldTests(unittest.TestCase):
    def test_sample_config_loads(self) -> None:
        config = load_app_config(SAMPLE_CONFIG)
        self.assertEqual(config.tracker.project_id, "founder-autopilot")
        self.assertEqual(config.daemon.poll_interval_seconds, 300)
        self.assertEqual(
            config.tracker.notification_channels,
            ["codex", "dashboard", "os"],
        )
        self.assertGreaterEqual(len(config.tracker.watch_paths), 1)

    def test_daemon_bootstrap_initializes_database(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database_path = Path(temp_dir) / "founder_autopilot.db"
            service = DaemonService(
                SAMPLE_CONFIG,
                database_path=database_path,
            )

            applied = service.bootstrap()

            self.assertIn("0001_initial_schema.sql", applied)
            self.assertTrue(database_path.exists())

            connection = sqlite3.connect(database_path)
            try:
                tables = {
                    row[0]
                    for row in connection.execute(
                        "SELECT name FROM sqlite_master WHERE type = 'table';"
                    )
                }
            finally:
                connection.close()
            self.assertIn("projects", tables)
            self.assertIn("tracker_configs", tables)
            self.assertIn("raw_events", tables)

    def test_database_override_updates_runtime_path(self) -> None:
        config = load_app_config(SAMPLE_CONFIG)
        override = override_database_path(config, REPO_ROOT / "data" / "override.db")
        self.assertTrue(override.daemon.database_path.endswith("override.db"))

    def test_ingestion_deduplicates_events_and_normalizes_order(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database_path = Path(temp_dir) / "events.db"
            database = Database(database_path)
            database.initialize()
            config = override_database_path(load_app_config(SAMPLE_CONFIG), database_path)
            database.bootstrap_project(config.tracker)
            worker = IngestionWorker(database, config.tracker.project_id)
            events = [
                SourceEvent(
                    source_event_id="commit-b",
                    observed_at="2026-03-06T12:00:00+01:00",
                    cursor=build_cursor("2026-03-06T12:00:00+01:00", "commit-b"),
                    payload={
                        "committedAt": "2026-03-06T12:00:00+01:00",
                        "commit": "commit-b",
                        "files": ["src/app.py"],
                        "repoPath": temp_dir,
                        "sourceEventId": "commit-b",
                        "summary": "Second commit",
                    },
                ),
                SourceEvent(
                    source_event_id="commit-a",
                    observed_at="2026-03-06T08:30:00-01:00",
                    cursor=build_cursor("2026-03-06T08:30:00-01:00", "commit-a"),
                    payload={
                        "committedAt": "2026-03-06T08:30:00-01:00",
                        "commit": "commit-a",
                        "files": ["README.md"],
                        "repoPath": temp_dir,
                        "sourceEventId": "commit-a",
                        "summary": "First commit",
                    },
                ),
                SourceEvent(
                    source_event_id="commit-a",
                    observed_at="2026-03-06T08:30:00-01:00",
                    cursor=build_cursor("2026-03-06T08:30:00-01:00", "commit-a"),
                    payload={
                        "committedAt": "2026-03-06T08:30:00-01:00",
                        "commit": "commit-a",
                        "files": ["README.md"],
                        "repoPath": temp_dir,
                        "sourceEventId": "commit-a",
                        "summary": "First commit",
                    },
                ),
            ]

            persisted = worker.ingest("git", events)
            activity_events = database.list_activity_events(config.tracker.project_id)

            self.assertEqual(persisted.received, 3)
            self.assertEqual(persisted.raw_inserted, 2)
            self.assertEqual(persisted.activity_inserted, 2)
            self.assertEqual(persisted.duplicates, 1)
            self.assertEqual(database.table_count("raw_events"), 2)
            self.assertEqual(
                [event.summary for event in activity_events],
                ["First commit", "Second commit"],
            )
            self.assertEqual(
                [event.timestamp for event in activity_events],
                ["2026-03-06T09:30:00+00:00", "2026-03-06T11:00:00+00:00"],
            )

    def test_invalid_events_are_quarantined(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database_path = Path(temp_dir) / "events.db"
            database = Database(database_path)
            database.initialize()
            config = override_database_path(load_app_config(SAMPLE_CONFIG), database_path)
            database.bootstrap_project(config.tracker)
            worker = IngestionWorker(database, config.tracker.project_id)

            persisted = worker.ingest(
                "cos",
                [
                    SourceEvent(
                        source_event_id="cos-1",
                        observed_at="2026-03-06T10:00:00+00:00",
                        cursor=build_cursor("2026-03-06T10:00:00+00:00", "cos-1"),
                        payload={
                            "timestamp": "not-a-timestamp",
                            "sourceEventId": "cos-1",
                        },
                    )
                ],
            )

            invalid_events = database.list_invalid_events(config.tracker.project_id)

            self.assertEqual(persisted.invalid, 1)
            self.assertEqual(database.table_count("activity_events"), 0)
            self.assertEqual(len(invalid_events), 1)
            self.assertIn("timestamp", invalid_events[0]["error_reason"])

    def test_git_adapter_collects_commits(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir) / "repo"
            repo_path.mkdir()
            self._run_git(repo_path, ["init"])
            self._run_git(repo_path, ["config", "user.email", "agent@example.com"])
            self._run_git(repo_path, ["config", "user.name", "Agent"])
            first_file = repo_path / "app.py"
            first_file.write_text("print('one')\n", encoding="utf-8")
            self._run_git(repo_path, ["add", "."])
            self._run_git(repo_path, ["commit", "-m", "Initial commit"])
            second_file = repo_path / "notes.md"
            second_file.write_text("# Notes\n", encoding="utf-8")
            self._run_git(repo_path, ["add", "."])
            self._run_git(repo_path, ["commit", "-m", "Add notes"])

            adapter = GitAdapter([str(repo_path)])
            events = adapter.collect(None)

            self.assertEqual(len(events), 2)
            self.assertEqual(events[0].payload["summary"], "Initial commit")
            self.assertEqual(events[1].payload["summary"], "Add notes")
            self.assertEqual(adapter.collect(events[-1].cursor), [])

    def test_cos_adapter_collects_jsonl_records(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            cos_dir = Path(temp_dir) / "data" / "cos"
            cos_dir.mkdir(parents=True)
            (cos_dir / "activity.jsonl").write_text(
                "\n".join(
                    [
                        "{\"id\":\"cos-1\",\"timestamp\":\"2026-03-06T09:00:00+00:00\",\"summary\":\"Drafted plan\",\"signalType\":\"planning\"}",
                        "{\"id\":\"cos-2\",\"timestamp\":\"2026-03-06T10:00:00+00:00\",\"summary\":\"Wrote docs\",\"signalType\":\"writing\"}",
                    ]
                ),
                encoding="utf-8",
            )

            adapter = COSAdapter([str(cos_dir)])
            events = adapter.collect(None)

            self.assertEqual(
                [event.source_event_id for event in events],
                ["cos-1", "cos-2"],
            )
            self.assertEqual(adapter.collect(events[-1].cursor), [])

    def test_filesystem_adapter_respects_exclusions(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            watch_dir = root / "watch"
            excluded_dir = root / "excluded"
            watch_dir.mkdir()
            excluded_dir.mkdir()
            (watch_dir / "keep.py").write_text("print('watch')\n", encoding="utf-8")
            (excluded_dir / "skip.py").write_text("print('skip')\n", encoding="utf-8")

            adapter = FileSystemAdapter(
                [str(watch_dir), str(excluded_dir)],
                [str(excluded_dir)],
            )
            events = adapter.collect(None)

            self.assertEqual(len(events), 1)
            self.assertEqual(events[0].payload["relativePath"], "keep.py")

    def test_daemon_default_adapters_capture_all_sources_and_resume(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir) / "project"
            config_dir = project_root / "config"
            tracked_dir = project_root / "tracked"
            data_cos_dir = project_root / "data" / "cos"
            config_dir.mkdir(parents=True)
            tracked_dir.mkdir()
            data_cos_dir.mkdir(parents=True)

            self._run_git(project_root, ["init"])
            self._run_git(project_root, ["config", "user.email", "agent@example.com"])
            self._run_git(project_root, ["config", "user.name", "Agent"])
            tracked_file = tracked_dir / "feature.py"
            tracked_file.write_text("print('tracked')\n", encoding="utf-8")
            self._run_git(project_root, ["add", "."])
            self._run_git(project_root, ["commit", "-m", "Track feature"])
            (data_cos_dir / "events.jsonl").write_text(
                "{\"id\":\"cos-1\",\"timestamp\":\"2026-03-06T12:00:00+00:00\",\"summary\":\"Reviewed task\",\"signalType\":\"planning\"}\n",
                encoding="utf-8",
            )
            config_path = config_dir / "tracker.toml"
            config_path.write_text(
                "\n".join(
                    [
                        'project_id = "founder-autopilot"',
                        'watch_paths = ["../tracked"]',
                        'excluded_paths = ["../tracked/.ignored"]',
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
                        "poll_interval_seconds = 300",
                        'database_path = "../data/founder_autopilot.db"',
                        'log_level = "INFO"',
                    ]
                ),
                encoding="utf-8",
            )

            service = DaemonService(config_path)
            service.bootstrap()

            first_cycle = service.run_cycle()
            second_cycle = service.run_cycle()
            sources = {
                event.source
                for event in service.database.list_activity_events("founder-autopilot")
            }

            self.assertEqual(first_cycle["git"], 1)
            self.assertEqual(first_cycle["cos"], 1)
            self.assertGreaterEqual(first_cycle["filesystem"], 1)
            self.assertEqual(second_cycle, {"git": 0, "cos": 0, "filesystem": 0})
            self.assertEqual(sources, {"git", "cos", "filesystem"})

    def _run_git(self, repo_path: Path, arguments: list[str]) -> None:
        subprocess.run(
            ["git", "-C", str(repo_path), *arguments],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )


if __name__ == "__main__":
    unittest.main()
