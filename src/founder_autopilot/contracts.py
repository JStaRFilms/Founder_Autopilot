from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

MetadataValue = str | int | float | bool | None
ActivitySource = Literal["git", "cos", "filesystem", "manual"]
SignalType = Literal["code", "writing", "planning", "research", "ops", "unknown"]
Trend = Literal["up", "flat", "down"]
NudgeType = Literal["focus", "break", "prioritize", "review"]
NudgeSeverity = Literal["low", "medium", "high"]
DeliveryChannel = Literal["codex", "dashboard", "os"]
NudgeStatus = Literal["pending", "delivered", "dismissed", "snoozed"]
Sensitivity = Literal["low", "medium", "high"]

DEFAULT_SIGNAL_WEIGHTS: dict[str, float] = {
    "code": 1.0,
    "writing": 0.8,
    "planning": 0.7,
    "research": 0.5,
    "ops": 0.4,
    "unknown": 0.2,
}


@dataclass(slots=True)
class QuietHours:
    start: str
    end: str
    timezone: str

    def to_contract_dict(self) -> dict[str, str]:
        return {
            "start": self.start,
            "end": self.end,
            "timezone": self.timezone,
        }


@dataclass(slots=True)
class SignalContribution:
    signal: str
    weight: float
    impact: float

    def to_contract_dict(self) -> dict[str, str | float]:
        return {
            "signal": self.signal,
            "weight": self.weight,
            "impact": self.impact,
        }


@dataclass(slots=True)
class ActivityEvent:
    id: str
    source: ActivitySource
    timestamp: str
    actor: Literal["founder"]
    project_id: str
    signal_type: SignalType
    summary: str
    metadata: dict[str, MetadataValue]

    def to_contract_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "source": self.source,
            "timestamp": self.timestamp,
            "actor": self.actor,
            "projectId": self.project_id,
            "signalType": self.signal_type,
            "summary": self.summary,
            "metadata": self.metadata,
        }


@dataclass(slots=True)
class ProjectSignal:
    id: str
    project_id: str
    window_start: str
    window_end: str
    focus_minutes: int
    drift_minutes: int
    context_switch_count: int
    confidence: float
    derived_from_event_ids: list[str] = field(default_factory=list)

    def to_contract_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "projectId": self.project_id,
            "windowStart": self.window_start,
            "windowEnd": self.window_end,
            "focusMinutes": self.focus_minutes,
            "driftMinutes": self.drift_minutes,
            "contextSwitchCount": self.context_switch_count,
            "confidence": self.confidence,
            "derivedFromEventIds": list(self.derived_from_event_ids),
        }


@dataclass(slots=True)
class FocusScore:
    id: str
    project_id: str
    date: str
    score: int
    trend: Trend
    contributing_signals: list[SignalContribution] = field(default_factory=list)
    computed_at: str = ""

    def to_contract_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "projectId": self.project_id,
            "date": self.date,
            "score": self.score,
            "trend": self.trend,
            "contributingSignals": [
                contribution.to_contract_dict()
                for contribution in self.contributing_signals
            ],
            "computedAt": self.computed_at,
        }


@dataclass(slots=True)
class Nudge:
    id: str
    created_at: str
    type: NudgeType
    severity: NudgeSeverity
    title: str
    message: str
    reason: str
    target_channels: list[DeliveryChannel] = field(default_factory=list)
    status: NudgeStatus = "pending"

    def to_contract_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "createdAt": self.created_at,
            "type": self.type,
            "severity": self.severity,
            "title": self.title,
            "message": self.message,
            "reason": self.reason,
            "targetChannels": list(self.target_channels),
            "status": self.status,
        }


@dataclass(slots=True)
class CycleReport:
    id: str
    project_id: str
    period_start: str
    period_end: str
    average_focus_score: float
    top_wins: list[str] = field(default_factory=list)
    drift_patterns: list[str] = field(default_factory=list)
    recommended_actions: list[str] = field(default_factory=list)
    generated_at: str = ""

    def to_contract_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "projectId": self.project_id,
            "periodStart": self.period_start,
            "periodEnd": self.period_end,
            "averageFocusScore": self.average_focus_score,
            "topWins": list(self.top_wins),
            "driftPatterns": list(self.drift_patterns),
            "recommendedActions": list(self.recommended_actions),
            "generatedAt": self.generated_at,
        }


@dataclass(slots=True)
class TrackerConfig:
    project_id: str
    watch_paths: list[str]
    excluded_paths: list[str]
    signal_weights: dict[str, float]
    quiet_hours: QuietHours
    nudge_sensitivity: Sensitivity
    notification_channels: list[DeliveryChannel]

    def to_contract_dict(self) -> dict[str, object]:
        return {
            "projectId": self.project_id,
            "watchPaths": list(self.watch_paths),
            "excludedPaths": list(self.excluded_paths),
            "signalWeights": dict(self.signal_weights),
            "quietHours": self.quiet_hours.to_contract_dict(),
            "nudgeSensitivity": self.nudge_sensitivity,
            "notificationChannels": list(self.notification_channels),
        }


@dataclass(slots=True)
class NotificationToggles:
    codex: bool = True
    dashboard: bool = True
    os: bool = True

    def enabled_channels(self) -> list[DeliveryChannel]:
        channels: list[DeliveryChannel] = []
        if self.codex:
            channels.append("codex")
        if self.dashboard:
            channels.append("dashboard")
        if self.os:
            channels.append("os")
        return channels

    def to_document_dict(self) -> dict[str, bool]:
        return {
            "codex": self.codex,
            "dashboard": self.dashboard,
            "os": self.os,
        }


@dataclass(slots=True)
class DaemonSettings:
    poll_interval_seconds: int
    database_path: str
    log_level: str = "INFO"

    def to_document_dict(self) -> dict[str, str | int]:
        return {
            "poll_interval_seconds": self.poll_interval_seconds,
            "database_path": self.database_path,
            "log_level": self.log_level,
        }


@dataclass(slots=True)
class AppConfig:
    tracker: TrackerConfig
    daemon: DaemonSettings
    notifications: NotificationToggles

    def to_document_dict(self) -> dict[str, object]:
        return {
            "project_id": self.tracker.project_id,
            "watch_paths": list(self.tracker.watch_paths),
            "excluded_paths": list(self.tracker.excluded_paths),
            "nudge_sensitivity": self.tracker.nudge_sensitivity,
            "signal_weights": dict(self.tracker.signal_weights),
            "quiet_hours": self.tracker.quiet_hours.to_contract_dict(),
            "notifications": self.notifications.to_document_dict(),
            "daemon": self.daemon.to_document_dict(),
        }
