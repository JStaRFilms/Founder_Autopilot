from __future__ import annotations

from pathlib import Path
import sqlite3
import tempfile
import unittest

from founder_autopilot.config import load_app_config, override_database_path
from founder_autopilot.daemon import DaemonService


REPO_ROOT = Path(__file__).resolve().parents[1]
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


if __name__ == "__main__":
    unittest.main()
