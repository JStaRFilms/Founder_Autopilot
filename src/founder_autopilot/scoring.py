from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, time, timedelta

from founder_autopilot.contracts import (
    ActivityEvent,
    FocusScore,
    ProjectSignal,
    SignalContribution,
    TrackerConfig,
)
from founder_autopilot.normalization import make_deterministic_id
from founder_autopilot.scheduler import ensure_datetime, load_timezone, to_utc_iso


POSITIVE_SIGNALS = {"code", "writing", "planning"}
NEGATIVE_SIGNALS = {"research", "ops", "unknown"}
MIN_EVENT_MINUTES = 5
DEFAULT_TAIL_MINUTES = 15
MAX_EVENT_MINUTES = 45


@dataclass(slots=True)
class ActivityAssessment:
    project_signal: ProjectSignal
    score: int
    contributing_signals: list[SignalContribution]
    momentum_score: int
    drift_score: int
    overload_score: int
    event_count: int


@dataclass(slots=True)
class DailyScoreCard:
    date: str
    assessment: ActivityAssessment
    focus_score: FocusScore


class ScoringEngine:
    def __init__(self, tracker_config: TrackerConfig, *, timezone_name: str) -> None:
        self.tracker_config = tracker_config
        self.timezone = load_timezone(timezone_name)

    def assess_window(
        self,
        *,
        project_id: str,
        events: list[ActivityEvent],
        window_start: datetime,
        window_end: datetime,
    ) -> ActivityAssessment | None:
        normalized_start = ensure_datetime(window_start).astimezone(self.timezone)
        normalized_end = ensure_datetime(window_end).astimezone(self.timezone)
        window_events = [
            event
            for event in sorted(events, key=lambda item: (item.timestamp, item.id))
            if normalized_start <= ensure_datetime(event.timestamp).astimezone(self.timezone) < normalized_end
        ]
        if not window_events:
            return None

        event_minutes = self._event_minutes(window_events)
        contributions_map: dict[str, float] = defaultdict(float)
        focus_minutes = 0
        drift_minutes = 0
        for event, minutes in zip(window_events, event_minutes):
            weight = self.tracker_config.signal_weights.get(
                event.signal_type,
                self.tracker_config.signal_weights.get("unknown", 0.2),
            )
            direction = 1 if event.signal_type in POSITIVE_SIGNALS else -1
            impact = round(direction * minutes * weight / 6, 1)
            contributions_map[event.signal_type] += impact
            if direction > 0:
                focus_minutes += minutes
            else:
                drift_minutes += minutes

        context_switch_count = self._context_switch_count(window_events)
        confidence = self._confidence(window_events, focus_minutes + drift_minutes)
        project_signal = ProjectSignal(
            id=make_deterministic_id(
                "sig",
                project_id,
                to_utc_iso(normalized_start),
                to_utc_iso(normalized_end),
            ),
            project_id=project_id,
            window_start=to_utc_iso(normalized_start),
            window_end=to_utc_iso(normalized_end),
            focus_minutes=focus_minutes,
            drift_minutes=drift_minutes,
            context_switch_count=context_switch_count,
            confidence=confidence,
            derived_from_event_ids=[event.id for event in window_events],
        )
        contributions = [
            SignalContribution(
                signal=signal,
                weight=self.tracker_config.signal_weights.get(
                    signal,
                    self.tracker_config.signal_weights.get("unknown", 0.2),
                ),
                impact=round(impact, 1),
            )
            for signal, impact in sorted(
                contributions_map.items(),
                key=lambda item: (-abs(item[1]), item[0]),
            )
        ]
        momentum_score = clamp(
            round(
                focus_minutes * 0.7
                + self._longest_focus_streak(window_events, event_minutes) * 0.4
                - drift_minutes * 0.2
            )
        )
        drift_score = clamp(
            round(drift_minutes * 1.25 + context_switch_count * 6 - focus_minutes * 0.15)
        )
        overload_score = clamp(
            round(max((focus_minutes + drift_minutes) - 240, 0) * 0.35 + max(context_switch_count - 6, 0) * 5)
        )
        score = clamp(
            round(
                55
                + sum(max(item.impact, 0.0) for item in contributions)
                + momentum_score * 0.1
                - sum(abs(min(item.impact, 0.0)) for item in contributions)
                - context_switch_count * 2.5
                - overload_score * 0.08
            )
        )
        return ActivityAssessment(
            project_signal=project_signal,
            score=score,
            contributing_signals=contributions,
            momentum_score=momentum_score,
            drift_score=drift_score,
            overload_score=overload_score,
            event_count=len(window_events),
        )

    def build_daily_scorecards(
        self,
        *,
        project_id: str,
        events: list[ActivityEvent],
        computed_at: str,
    ) -> list[DailyScoreCard]:
        localized_by_date: dict[str, list[ActivityEvent]] = defaultdict(list)
        for event in sorted(events, key=lambda item: (item.timestamp, item.id)):
            local_date = ensure_datetime(event.timestamp).astimezone(self.timezone).date().isoformat()
            localized_by_date[local_date].append(event)

        cards: list[DailyScoreCard] = []
        for score_date in sorted(localized_by_date):
            local_start = datetime.combine(
                datetime.fromisoformat(score_date).date(),
                time.min,
                tzinfo=self.timezone,
            )
            local_end = local_start + timedelta(days=1)
            assessment = self.assess_window(
                project_id=project_id,
                events=localized_by_date[score_date],
                window_start=local_start,
                window_end=local_end,
            )
            if assessment is None:
                continue
            cards.append(
                DailyScoreCard(
                    date=score_date,
                    assessment=assessment,
                    focus_score=FocusScore(
                        id=make_deterministic_id("score", project_id, score_date),
                        project_id=project_id,
                        date=score_date,
                        score=assessment.score,
                        trend="flat",
                        contributing_signals=list(assessment.contributing_signals),
                        computed_at=computed_at,
                    ),
                )
            )

        self._apply_trends(cards)
        return cards

    def _apply_trends(self, cards: list[DailyScoreCard]) -> None:
        for index, card in enumerate(cards):
            previous_scores = [item.focus_score.score for item in cards[max(0, index - 7):index]]
            if not previous_scores:
                card.focus_score.trend = "flat"
                continue
            delta = card.focus_score.score - (sum(previous_scores) / len(previous_scores))
            if delta >= 4:
                card.focus_score.trend = "up"
            elif delta <= -4:
                card.focus_score.trend = "down"
            else:
                card.focus_score.trend = "flat"

    def _confidence(self, events: list[ActivityEvent], active_minutes: int) -> float:
        source_count = len({event.source for event in events})
        confidence = 0.35 + min(len(events), 8) * 0.06 + min(source_count, 3) * 0.08 + min(active_minutes, 240) / 600
        return round(min(confidence, 1.0), 2)

    def _context_switch_count(self, events: list[ActivityEvent]) -> int:
        switches = 0
        for previous, current in zip(events, events[1:]):
            previous_at = ensure_datetime(previous.timestamp)
            current_at = ensure_datetime(current.timestamp)
            gap_minutes = max((current_at - previous_at).total_seconds() / 60, 0)
            if gap_minutes > 90:
                continue
            if previous.signal_type != current.signal_type or previous.source != current.source:
                switches += 1
        return switches

    def _event_minutes(self, events: list[ActivityEvent]) -> list[int]:
        durations: list[int] = []
        for index, event in enumerate(events):
            if index + 1 >= len(events):
                durations.append(DEFAULT_TAIL_MINUTES)
                continue
            current_at = ensure_datetime(event.timestamp)
            next_at = ensure_datetime(events[index + 1].timestamp)
            delta_minutes = max((next_at - current_at).total_seconds() / 60, 0)
            bounded = max(MIN_EVENT_MINUTES, min(MAX_EVENT_MINUTES, round(delta_minutes)))
            durations.append(bounded)
        return durations

    def _longest_focus_streak(
        self,
        events: list[ActivityEvent],
        durations: list[int],
    ) -> int:
        longest = 0
        current = 0
        for event, duration in zip(events, durations):
            if event.signal_type in POSITIVE_SIGNALS:
                current += duration
                longest = max(longest, current)
            else:
                current = 0
        return longest


def clamp(value: int) -> int:
    return max(0, min(100, value))
