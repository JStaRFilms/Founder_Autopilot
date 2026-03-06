from __future__ import annotations

import argparse
from pathlib import Path

from founder_autopilot.analytics import AnalyticsService
from founder_autopilot.config import ConfigValidationError, load_app_config
from founder_autopilot.daemon import DaemonService


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="founder-autopilot")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_db_parser = subparsers.add_parser(
        "init-db",
        help="Apply SQLite migrations and persist the current tracker config.",
    )
    _add_shared_arguments(init_db_parser)

    validate_parser = subparsers.add_parser(
        "validate-config",
        help="Load the config file and report the validated result.",
    )
    validate_parser.add_argument(
        "--config",
        default="config/tracker.sample.toml",
        help="Path to the TOML configuration file.",
    )

    run_parser = subparsers.add_parser(
        "run-daemon",
        help="Start the local daemon scaffold.",
    )
    _add_shared_arguments(run_parser)
    run_parser.add_argument(
        "--once",
        action="store_true",
        help="Run a single daemon cycle and exit.",
    )

    analytics_parser = subparsers.add_parser(
        "generate-reports",
        help="Recompute scores and generate the current daily and cycle reports.",
    )
    _add_shared_arguments(analytics_parser)
    analytics_parser.add_argument(
        "--at",
        help="Optional ISO-8601 timestamp used as the scheduler reference time.",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "validate-config":
            config = load_app_config(args.config)
            print(f"Config valid: {Path(args.config).resolve()}")
            print(f"Project: {config.tracker.project_id}")
            print(f"Watch paths: {len(config.tracker.watch_paths)}")
            print(f"Poll interval: {config.daemon.poll_interval_seconds}s")
            print(
                "Channels: "
                + ", ".join(config.tracker.notification_channels)
            )
            return 0

        service = DaemonService(
            args.config,
            database_path=args.db,
        )

        if args.command == "init-db":
            applied = service.bootstrap()
            print(
                "Database ready: "
                f"{service.database.database_path} | applied={applied or ['none']}"
            )
            return 0

        if args.command == "run-daemon":
            service.run(once=args.once)
            return 0

        if args.command == "generate-reports":
            service.bootstrap()
            snapshot = service.analytics.refresh(as_of=args.at)
            print(f"Computed daily scores: {len(snapshot.daily_scorecards)}")
            if snapshot.daily_report is None:
                print("Daily report: none due for the current schedule window")
            else:
                print(
                    "Daily report window: "
                    f"{snapshot.daily_report.window_start} -> {snapshot.daily_report.window_end}"
                )
                print(snapshot.daily_report.summary)
            if snapshot.cycle_report is None:
                print("Cycle report: no scored data in the active cycle")
            else:
                print(
                    "Cycle report window: "
                    f"{snapshot.cycle_report.period_start} -> {snapshot.cycle_report.period_end}"
                )
                print(
                    "Average focus score: "
                    f"{snapshot.cycle_report.average_focus_score}"
                )
            return 0
    except ConfigValidationError as exc:
        parser.error(str(exc))

    parser.error(f"Unsupported command: {args.command}")
    return 2


def _add_shared_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--config",
        default="config/tracker.sample.toml",
        help="Path to the TOML configuration file.",
    )
    parser.add_argument(
        "--db",
        help="Optional database path override.",
    )
