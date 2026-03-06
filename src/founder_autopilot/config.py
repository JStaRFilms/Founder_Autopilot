from __future__ import annotations

from dataclasses import replace
from datetime import datetime
from pathlib import Path
import re
import tomllib
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from founder_autopilot.contracts import (
    AppConfig,
    DEFAULT_SIGNAL_WEIGHTS,
    DaemonSettings,
    NotificationToggles,
    QuietHours,
    SchedulerSettings,
    Sensitivity,
    TrackerConfig,
)
from founder_autopilot.scheduler import (
    DEFAULT_CYCLE_ANCHOR_DATE,
    DEFAULT_CYCLE_LENGTH_DAYS,
    DEFAULT_SUMMARY_TIMES,
)


class ConfigValidationError(ValueError):
    """Raised when the tracker configuration file is invalid."""


def load_app_config(config_path: str | Path) -> AppConfig:
    path = Path(config_path).expanduser().resolve()
    if not path.exists():
        raise ConfigValidationError(f"Config file does not exist: {path}")

    with path.open("rb") as handle:
        raw = tomllib.load(handle)

    notifications = _parse_notifications(raw.get("notifications", {}))
    tracker = TrackerConfig(
        project_id=_require_non_empty_string(raw.get("project_id"), "project_id"),
        watch_paths=_parse_paths(raw.get("watch_paths"), "watch_paths", path.parent),
        excluded_paths=_parse_paths(
            raw.get("excluded_paths", []),
            "excluded_paths",
            path.parent,
            require_existing=False,
        ),
        signal_weights=_parse_signal_weights(raw.get("signal_weights", {})),
        quiet_hours=_parse_quiet_hours(raw.get("quiet_hours", {})),
        nudge_sensitivity=_parse_sensitivity(raw.get("nudge_sensitivity", "medium")),
        notification_channels=notifications.enabled_channels(),
    )
    daemon = _parse_daemon(raw.get("daemon", {}), path.parent)
    scheduler = _parse_scheduler(
        raw.get("scheduler", {}),
        default_timezone=tracker.quiet_hours.timezone,
    )
    return AppConfig(
        tracker=tracker,
        daemon=daemon,
        notifications=notifications,
        scheduler=scheduler,
    )


def override_database_path(config: AppConfig, database_path: str | Path) -> AppConfig:
    path = Path(database_path).expanduser().resolve()
    return replace(
        config,
        daemon=replace(config.daemon, database_path=str(path)),
    )


def _parse_notifications(raw: object) -> NotificationToggles:
    mapping = _require_mapping(raw, "notifications")
    toggles = NotificationToggles(
        codex=_require_bool(mapping.get("codex", True), "notifications.codex"),
        dashboard=_require_bool(
            mapping.get("dashboard", True),
            "notifications.dashboard",
        ),
        os=_require_bool(mapping.get("os", True), "notifications.os"),
    )
    if not toggles.enabled_channels():
        raise ConfigValidationError(
            "At least one notification channel must be enabled."
        )
    return toggles


def _parse_daemon(raw: object, base_dir: Path) -> DaemonSettings:
    mapping = _require_mapping(raw, "daemon")
    poll_interval_seconds = _require_positive_int(
        mapping.get("poll_interval_seconds", 300),
        "daemon.poll_interval_seconds",
    )
    database_path = mapping.get("database_path", "../data/founder_autopilot.db")
    if not isinstance(database_path, str) or not database_path.strip():
        raise ConfigValidationError("daemon.database_path must be a non-empty string.")
    resolved_database_path = str((base_dir / database_path).expanduser().resolve())
    log_level = _require_non_empty_string(
        mapping.get("log_level", "INFO"),
        "daemon.log_level",
    )
    return DaemonSettings(
        poll_interval_seconds=poll_interval_seconds,
        database_path=resolved_database_path,
        log_level=log_level.upper(),
    )


def _parse_signal_weights(raw: object) -> dict[str, float]:
    mapping = _require_mapping(raw, "signal_weights")
    weights = dict(DEFAULT_SIGNAL_WEIGHTS)
    for key, value in mapping.items():
        if not isinstance(key, str) or not key:
            raise ConfigValidationError("signal_weights keys must be non-empty strings.")
        if not isinstance(value, (int, float)):
            raise ConfigValidationError(
                f"signal_weights.{key} must be a number, got {type(value).__name__}."
            )
        if value < 0:
            raise ConfigValidationError(f"signal_weights.{key} cannot be negative.")
        weights[key] = float(value)
    return weights


def _parse_scheduler(raw: object, *, default_timezone: str) -> SchedulerSettings:
    mapping = _require_mapping(raw, "scheduler")
    summary_times_raw = mapping.get("summary_times", list(DEFAULT_SUMMARY_TIMES))
    if not isinstance(summary_times_raw, list) or not summary_times_raw:
        raise ConfigValidationError("scheduler.summary_times must be a non-empty list.")

    summary_times: list[str] = []
    for index, value in enumerate(summary_times_raw):
        if not isinstance(value, str) or not value.strip():
            raise ConfigValidationError(
                f"scheduler.summary_times[{index}] must be a non-empty HH:MM string."
            )
        normalized = value.strip()
        _validate_time_string(normalized, f"scheduler.summary_times[{index}]")
        if normalized not in summary_times:
            summary_times.append(normalized)
    cycle_length_days = _require_positive_int(
        mapping.get("cycle_length_days", DEFAULT_CYCLE_LENGTH_DAYS),
        "scheduler.cycle_length_days",
    )
    cycle_anchor_date = _require_non_empty_string(
        mapping.get("cycle_anchor_date", DEFAULT_CYCLE_ANCHOR_DATE),
        "scheduler.cycle_anchor_date",
    )
    try:
        datetime.strptime(cycle_anchor_date, "%Y-%m-%d")
    except ValueError as exc:
        raise ConfigValidationError(
            "scheduler.cycle_anchor_date must use YYYY-MM-DD format."
        ) from exc
    timezone = _require_non_empty_string(
        mapping.get("timezone", default_timezone),
        "scheduler.timezone",
    )
    _validate_timezone_string(timezone)
    return SchedulerSettings(
        summary_times=summary_times,
        cycle_length_days=cycle_length_days,
        cycle_anchor_date=cycle_anchor_date,
        timezone=timezone,
    )


def _parse_quiet_hours(raw: object) -> QuietHours:
    mapping = _require_mapping(raw, "quiet_hours")
    start = _require_non_empty_string(mapping.get("start"), "quiet_hours.start")
    end = _require_non_empty_string(mapping.get("end"), "quiet_hours.end")
    timezone = _require_non_empty_string(
        mapping.get("timezone"),
        "quiet_hours.timezone",
    )
    _validate_time_string(start, "quiet_hours.start")
    _validate_time_string(end, "quiet_hours.end")
    _validate_timezone_string(timezone)
    return QuietHours(start=start, end=end, timezone=timezone)


def _parse_sensitivity(raw: object) -> Sensitivity:
    if raw not in {"low", "medium", "high"}:
        raise ConfigValidationError(
            "nudge_sensitivity must be one of: low, medium, high."
        )
    return raw


def _parse_paths(
    raw: object,
    field_name: str,
    base_dir: Path,
    *,
    require_existing: bool = True,
) -> list[str]:
    if not isinstance(raw, list) or not raw:
        raise ConfigValidationError(f"{field_name} must be a non-empty list of paths.")

    resolved_paths: list[str] = []
    for index, value in enumerate(raw):
        if not isinstance(value, str) or not value.strip():
            raise ConfigValidationError(
                f"{field_name}[{index}] must be a non-empty string path."
            )
        resolved = (base_dir / value).expanduser().resolve()
        if require_existing and not resolved.exists():
            raise ConfigValidationError(
                f"{field_name}[{index}] does not exist: {resolved}"
            )
        resolved_paths.append(str(resolved))
    return resolved_paths


def _require_mapping(raw: object, field_name: str) -> dict[object, object]:
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise ConfigValidationError(f"{field_name} must be a table/object.")
    return raw


def _require_positive_int(raw: object, field_name: str) -> int:
    if isinstance(raw, bool) or not isinstance(raw, int) or raw <= 0:
        raise ConfigValidationError(f"{field_name} must be a positive integer.")
    return raw


def _require_bool(raw: object, field_name: str) -> bool:
    if not isinstance(raw, bool):
        raise ConfigValidationError(f"{field_name} must be a boolean.")
    return raw


def _require_non_empty_string(raw: object, field_name: str) -> str:
    if not isinstance(raw, str) or not raw.strip():
        raise ConfigValidationError(f"{field_name} must be a non-empty string.")
    return raw.strip()


def _validate_time_string(value: str, field_name: str) -> None:
    try:
        datetime.strptime(value, "%H:%M")
    except ValueError as exc:
        raise ConfigValidationError(
            f"{field_name} must use HH:MM 24-hour format."
        ) from exc


def _validate_timezone_string(value: str) -> None:
    try:
        ZoneInfo(value)
        return
    except ZoneInfoNotFoundError:
        # Windows Python often lacks bundled tzdata. Accept canonical IANA-like
        # keys so local config validation stays dependency-free.
        if re.fullmatch(r"[A-Za-z_+-]+(?:/[A-Za-z0-9_+-]+)+", value):
            return
        raise ConfigValidationError(
            f"quiet_hours.timezone is not a valid IANA timezone key: {value}"
        )
