from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from founder_autopilot.config import load_app_config, override_database_path
from founder_autopilot.contracts import AppConfig, CycleReport, DailyReport
from founder_autopilot.database import Database, utc_now_iso
from founder_autopilot.reporting import ReportGenerator
from founder_autopilot.scheduler import CadenceScheduler, ensure_datetime
from founder_autopilot.scoring import DailyScoreCard, ScoringEngine


@dataclass(slots=True)
class AnalyticsSnapshot:
    daily_scorecards: list[DailyScoreCard]
    daily_report: DailyReport | None
    cycle_report: CycleReport | None


class AnalyticsService:
    def __init__(self, database: Database, config: AppConfig) -> None:
        self.database = database
        self.config = config
        self.scoring = ScoringEngine(
            config.tracker,
            timezone_name=config.scheduler.timezone,
        )
        self.scheduler = CadenceScheduler(config.scheduler)
        self.reporting = ReportGenerator()

    def refresh(self, *, as_of: datetime | str | None = None) -> AnalyticsSnapshot:
        generated_at = utc_now_iso()
        reference_time = ensure_datetime(as_of or generated_at)
        events = self.database.list_activity_events(self.config.tracker.project_id)
        daily_scorecards = self.scoring.build_daily_scorecards(
            project_id=self.config.tracker.project_id,
            events=events,
            computed_at=generated_at,
        )
        for card in daily_scorecards:
            self.database.upsert_project_signal(card.assessment.project_signal)
            self.database.upsert_focus_score(card.focus_score)

        scheduled_window = self.scheduler.current_summary_window(reference_time)
        window_assessment = self.scoring.assess_window(
            project_id=self.config.tracker.project_id,
            events=events,
            window_start=scheduled_window.window_start,
            window_end=scheduled_window.window_end,
        )
        daily_report = self.reporting.generate_daily_report(
            project_id=self.config.tracker.project_id,
            assessment=window_assessment,
            scheduled_window=scheduled_window,
            generated_at=generated_at,
        )
        cycle_window = self.scheduler.cycle_window_for(reference_time)
        cycle_report = self.reporting.generate_cycle_report(
            project_id=self.config.tracker.project_id,
            cycle_window=cycle_window,
            daily_scorecards=daily_scorecards,
            events=events,
            generated_at=generated_at,
        )
        if cycle_report is not None:
            self.database.upsert_cycle_report(cycle_report)
        return AnalyticsSnapshot(
            daily_scorecards=daily_scorecards,
            daily_report=daily_report,
            cycle_report=cycle_report,
        )


def build_analytics_service(
    config_path: str,
    *,
    database_path: str | None = None,
) -> AnalyticsService:
    config = load_app_config(config_path)
    if database_path is not None:
        config = override_database_path(config, database_path)
    return AnalyticsService(Database(config.daemon.database_path), config)
