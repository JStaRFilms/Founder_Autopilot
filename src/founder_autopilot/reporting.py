from __future__ import annotations

from dataclasses import dataclass

from founder_autopilot.contracts import ActivityEvent, CycleReport, DailyReport
from founder_autopilot.normalization import make_deterministic_id
from founder_autopilot.scheduler import CycleWindow, ScheduledWindow, ensure_datetime
from founder_autopilot.scoring import ActivityAssessment, DailyScoreCard, NEGATIVE_SIGNALS, POSITIVE_SIGNALS


@dataclass(slots=True)
class GeneratedReports:
    daily_report: DailyReport | None
    cycle_report: CycleReport | None


class ReportGenerator:
    def generate_daily_report(
        self,
        *,
        project_id: str,
        assessment: ActivityAssessment | None,
        scheduled_window: ScheduledWindow,
        generated_at: str,
    ) -> DailyReport | None:
        if assessment is None:
            return None

        focus_minutes = assessment.project_signal.focus_minutes
        drift_minutes = assessment.project_signal.drift_minutes
        switches = assessment.project_signal.context_switch_count
        summary = (
            f"Focus score {assessment.score} with {focus_minutes} focus minutes, "
            f"{drift_minutes} drift minutes, and {switches} context switches in this block."
        )
        top_wins = self._top_wins_from_assessment(assessment)
        drift_risks = self._drift_risks_from_assessment(assessment)
        recommended_actions = self._recommended_actions_from_assessment(assessment)
        return DailyReport(
            id=make_deterministic_id(
                "daily",
                project_id,
                scheduled_window.window_start,
                scheduled_window.window_end,
            ),
            project_id=project_id,
            window_start=scheduled_window.window_start,
            window_end=scheduled_window.window_end,
            focus_score=assessment.score,
            momentum_score=assessment.momentum_score,
            drift_score=assessment.drift_score,
            overload_score=assessment.overload_score,
            summary=summary,
            top_wins=top_wins,
            drift_risks=drift_risks,
            recommended_actions=recommended_actions,
            generated_at=generated_at,
        )

    def generate_cycle_report(
        self,
        *,
        project_id: str,
        cycle_window: CycleWindow,
        daily_scorecards: list[DailyScoreCard],
        events: list[ActivityEvent],
        generated_at: str,
    ) -> CycleReport | None:
        cycle_cards = [
            card
            for card in daily_scorecards
            if cycle_window.start <= card.assessment.project_signal.window_start
            and card.assessment.project_signal.window_end <= cycle_window.end
        ]
        if not cycle_cards:
            return None

        cycle_events = [
            event
            for event in events
            if cycle_window.start <= event.timestamp < cycle_window.end
        ]
        average_focus_score = round(
            sum(card.focus_score.score for card in cycle_cards) / len(cycle_cards),
            1,
        )
        top_wins = self._cycle_top_wins(cycle_cards)
        drift_patterns = self._cycle_drift_patterns(cycle_cards, cycle_events)
        recommended_actions = self._cycle_actions(cycle_cards)
        return CycleReport(
            id=make_deterministic_id("cycle", project_id, cycle_window.start, cycle_window.end),
            project_id=project_id,
            period_start=cycle_window.start,
            period_end=cycle_window.end,
            average_focus_score=average_focus_score,
            top_wins=top_wins,
            drift_patterns=drift_patterns,
            recommended_actions=recommended_actions,
            generated_at=generated_at,
        )

    def _top_wins_from_assessment(self, assessment: ActivityAssessment) -> list[str]:
        wins = [
            f"{item.signal.title()} contributed {item.impact:+.1f} to the score."
            for item in assessment.contributing_signals
            if item.signal in POSITIVE_SIGNALS and item.impact > 0
        ]
        if assessment.momentum_score >= 70:
            wins.append("Momentum stayed high enough to protect a meaningful work block.")
        return wins[:3] or ["Activity stayed mostly aligned with core work."]

    def _drift_risks_from_assessment(self, assessment: ActivityAssessment) -> list[str]:
        risks = [
            f"{item.signal.title()} pulled the score down by {abs(item.impact):.1f}."
            for item in assessment.contributing_signals
            if item.signal in NEGATIVE_SIGNALS and item.impact < 0
        ]
        if assessment.project_signal.context_switch_count >= 3:
            risks.append(
                f"{assessment.project_signal.context_switch_count} context switches fragmented the block."
            )
        if assessment.overload_score >= 60:
            risks.append("Active minutes crossed the overload threshold for this block.")
        return risks[:3] or ["No major drift pattern was detected in this block."]

    def _recommended_actions_from_assessment(self, assessment: ActivityAssessment) -> list[str]:
        actions: list[str] = []
        if assessment.drift_score >= 60:
            actions.append("Trim research and ops work into one bounded follow-up slot.")
        if assessment.project_signal.context_switch_count >= 3:
            actions.append("Stay on one source and one signal type for the next block.")
        if assessment.overload_score >= 60:
            actions.append("Take a short break before starting another focus window.")
        if not actions:
            actions.append("Protect the next block and repeat the current working pattern.")
        return actions[:3]

    def _cycle_top_wins(self, daily_scorecards: list[DailyScoreCard]) -> list[str]:
        top_day = max(daily_scorecards, key=lambda card: card.focus_score.score)
        wins = [
            f"Best day landed at focus score {top_day.focus_score.score} on {top_day.date}.",
        ]
        strong_days = [card for card in daily_scorecards if card.focus_score.score >= 70]
        if strong_days:
            wins.append(f"{len(strong_days)} days cleared the strong-focus threshold of 70.")
        stable_days = [
            card
            for card in daily_scorecards
            if card.assessment.project_signal.context_switch_count <= 2
        ]
        if stable_days:
            wins.append(f"{len(stable_days)} days stayed at two or fewer context switches.")
        return wins[:3]

    def _cycle_drift_patterns(
        self,
        daily_scorecards: list[DailyScoreCard],
        events: list[ActivityEvent],
    ) -> list[str]:
        patterns: list[str] = []
        drift_days = [card for card in daily_scorecards if card.assessment.drift_score >= 55]
        if drift_days:
            patterns.append(f"{len(drift_days)} days showed elevated drift pressure.")
        negative_events = [event for event in events if event.signal_type in NEGATIVE_SIGNALS]
        if negative_events:
            dominant = self._dominant_signal(negative_events)
            patterns.append(f"{dominant.title()} was the most common drift source in the cycle.")
        overloaded_days = [card for card in daily_scorecards if card.assessment.overload_score >= 55]
        if overloaded_days:
            patterns.append("Long, fragmented days drove overload late in the cycle.")
        return patterns[:3] or ["No repeated drift pattern stood out across the cycle."]

    def _cycle_actions(self, daily_scorecards: list[DailyScoreCard]) -> list[str]:
        actions: list[str] = []
        average_switches = sum(
            card.assessment.project_signal.context_switch_count for card in daily_scorecards
        ) / len(daily_scorecards)
        if average_switches >= 3:
            actions.append("Protect the first work block from context switches.")
        if any(card.assessment.overload_score >= 60 for card in daily_scorecards):
            actions.append("Cap intensive work blocks before overload rises above 60.")
        if not actions:
            actions.append("Keep the same cadence and scoring weights for the next cycle.")
        actions.append("Review the lowest-scoring day and remove one repeatable drift trigger.")
        return actions[:3]

    def _dominant_signal(self, events: list[ActivityEvent]) -> str:
        counts: dict[str, int] = {}
        for event in events:
            counts[event.signal_type] = counts.get(event.signal_type, 0) + 1
        return sorted(counts.items(), key=lambda item: (-item[1], item[0]))[0][0]
