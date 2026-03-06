from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from founder_autopilot.contracts import SchedulerSettings


DEFAULT_SUMMARY_TIMES: tuple[str, str, str] = ("09:00", "13:00", "17:00")
DEFAULT_CYCLE_LENGTH_DAYS = 14
DEFAULT_CYCLE_ANCHOR_DATE = "2026-03-02"
_FIXED_OFFSET_TIMEZONES: dict[str, timezone] = {
    "Africa/Lagos": timezone(timedelta(hours=1), name="Africa/Lagos"),
}


@dataclass(slots=True)
class ScheduledWindow:
    scheduled_for: str
    window_start: str
    window_end: str


@dataclass(slots=True)
class CycleWindow:
    start: str
    end: str


class CadenceScheduler:
    def __init__(self, settings: SchedulerSettings) -> None:
        self.settings = settings
        self.timezone = load_timezone(settings.timezone)

    def current_summary_window(self, reference_time: datetime) -> ScheduledWindow:
        localized_reference = ensure_datetime(reference_time).astimezone(self.timezone)
        candidate_days = (
            localized_reference.date() - timedelta(days=1),
            localized_reference.date(),
            localized_reference.date() + timedelta(days=1),
        )
        candidate_slots = [
            slot
            for day in candidate_days
            for slot in self.summary_slots_for_day(day)
        ]
        due_slots = [slot for slot in candidate_slots if slot <= localized_reference]
        if not due_slots:
            raise ValueError("no scheduled summary slots available")

        end_slot = due_slots[-1]
        previous_slots = [slot for slot in candidate_slots if slot < end_slot]
        if previous_slots:
            start_slot = previous_slots[-1]
        else:
            interval_hours = max(1, round(24 / max(len(self.settings.summary_times), 1)))
            start_slot = end_slot - timedelta(hours=interval_hours)
        return ScheduledWindow(
            scheduled_for=to_utc_iso(end_slot),
            window_start=to_utc_iso(start_slot),
            window_end=to_utc_iso(end_slot),
        )

    def cycle_window_for(self, reference_time: datetime) -> CycleWindow:
        localized_reference = ensure_datetime(reference_time).astimezone(self.timezone)
        anchor_date = date.fromisoformat(self.settings.cycle_anchor_date)
        cycle_length = self.settings.cycle_length_days
        cycle_index = (localized_reference.date() - anchor_date).days // cycle_length
        cycle_start_date = anchor_date + timedelta(days=cycle_index * cycle_length)
        cycle_end_date = cycle_start_date + timedelta(days=cycle_length)
        cycle_start = datetime.combine(cycle_start_date, time.min, tzinfo=self.timezone)
        cycle_end = datetime.combine(cycle_end_date, time.min, tzinfo=self.timezone)
        return CycleWindow(
            start=to_utc_iso(cycle_start),
            end=to_utc_iso(cycle_end),
        )

    def summary_slots_for_day(self, on_date: date) -> list[datetime]:
        return sorted(
            datetime.combine(on_date, parse_clock_time(value), tzinfo=self.timezone)
            for value in self.settings.summary_times
        )


def build_scheduler_settings(
    *,
    timezone_name: str,
    summary_times: list[str] | None = None,
    cycle_length_days: int = DEFAULT_CYCLE_LENGTH_DAYS,
    cycle_anchor_date: str = DEFAULT_CYCLE_ANCHOR_DATE,
) -> SchedulerSettings:
    return SchedulerSettings(
        summary_times=list(summary_times or DEFAULT_SUMMARY_TIMES),
        cycle_length_days=cycle_length_days,
        cycle_anchor_date=cycle_anchor_date,
        timezone=timezone_name,
    )


def ensure_datetime(value: datetime | str) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    else:
        raw = value.strip()
        if raw.endswith("Z"):
            raw = raw[:-1] + "+00:00"
        parsed = datetime.fromisoformat(raw)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed


def load_timezone(name: str) -> ZoneInfo | timezone:
    try:
        return ZoneInfo(name)
    except ZoneInfoNotFoundError:
        fixed_offset = _FIXED_OFFSET_TIMEZONES.get(name)
        if fixed_offset is not None:
            return fixed_offset
        return UTC


def parse_clock_time(value: str) -> time:
    return datetime.strptime(value, "%H:%M").time()


def to_utc_iso(value: datetime) -> str:
    return ensure_datetime(value).astimezone(UTC).replace(microsecond=0).isoformat()
