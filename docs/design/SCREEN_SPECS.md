# Founder Autopilot Screen Specs

## Shared Behaviors
- All screens support keyboard-first navigation, a visible skip link, and responsive layouts at `375`, `768`, `1024`, and `1440`.
- The top bar exposes date scope, project selector, quick search, and notification access.
- Empty, loading, and error states are documented per screen because the product depends on local ingestion and may start without data.
- Right-side context panel appears on `lg+` when an explanation, event detail, or configuration helper is opened.

## Today

### Goal
Give the founder a fast daily read on focus quality and the next corrective action.

### Layout
- Hero score card with today's focus score, trend arrow, confidence, and last recompute timestamp.
- Secondary card row: deep-work minutes, context switches, active drift alerts, pending notifications.
- Main split:
  - left: live activity timeline preview
  - right: top reason cards and notification summary

### Key behaviors
- Hero card opens Focus screen filtered to today.
- "Why this score moved" opens explanation drawer with contributing signals.
- Top drift alert CTA routes to Drift Alerts and pre-filters current day.

### States
- Empty: onboarding-oriented message with required setup steps and links to Settings.
- Loading: skeleton cards and muted timeline placeholders.
- Error: compact inline status with last successful computation and retry action.

## Timeline

### Goal
Let the founder audit what happened and why the system interpreted it as focus or drift.

### Layout
- Sticky filter bar.
- Session summary strip with totals for selected period.
- Timeline list grouped by hour/session.
- Optional right detail panel for selected row.

### Row details
- timestamp
- source
- signal type
- summary
- metadata chips
- score impact note

### Behaviors
- Multi-filter combinations update without full page reload.
- Selecting a row keeps list position and opens detail panel.
- Dense days collapse into session groups with "show all events".

### States
- Empty result after filtering: show filter reset affordance and preserve selected chips.
- No activity for day: suggest checking daemon health or watch path configuration.

## Focus

### Goal
Explain scoring over time and make deep-work patterns visible.

### Layout
- Title and date range controls.
- Primary trend chart with confidence band.
- Breakdown cards for focus minutes, drift minutes, context switches, confidence.
- Contributing signals table with weights and impacts.
- Recommendation rail with concrete suggestions.

### Behaviors
- Chart legend toggles individual overlays.
- Hover/focus on chart updates summary callout.
- Switching time range updates chart and recommendations together.

### States
- Low confidence state explicitly warns that limited event coverage may affect interpretation.
- If data is sparse, replace chart with a narrative summary plus setup recommendation.

## Drift Alerts

### Goal
Make coaching interventions reviewable and actionable without feeling punitive.

### Layout
- Active alerts lane pinned at top.
- Historical alert feed below with severity, reason, channels, and status.
- Cooldown status panel showing when similar nudges can fire again.

### Behaviors
- Dismiss and snooze available inline.
- "Open context" deep-links to the related Timeline or Focus view.
- Severity filter and channel filter persist in URL/app state.

### States
- Empty: reinforce healthy day with explanation of alert logic.
- Delivery failure state: promote Notification Center link.

## Reports

### Goal
Support weekly review with a concise narrative and a history of prior cycles.

### Layout
- Current cycle report header with average focus score and period dates.
- Three equal-priority content blocks: wins, drift patterns, recommended actions.
- Historical report table or card stack beneath.

### Behaviors
- Selecting a prior report swaps detail view without leaving page.
- Recommended actions can be copied/exported in future implementation.
- Cross-links from drift pattern items to matching Timeline slices.

### States
- Before first report boundary: explain when first report will generate.
- Sparse data state: mark report as low confidence instead of failing silently.

## Settings

### Goal
Configure ingestion, scoring, and notification behavior safely.

### Layout
- Section navigation or anchored form:
  - Tracking
  - Exclusions
  - Signal weights
  - Quiet hours
  - Notification channels
  - Nudge sensitivity
- Sticky save bar on mobile and desktop when dirty.

### Field rules
- Watch paths: add/remove rows, validate existence, block duplicates.
- Excluded paths: tag or path-list input with path conflict warning.
- Signal weights: numeric controls with default reset.
- Quiet hours: start/end time plus timezone summary.
- Channels: checkbox or segmented toggles with delivery notes.

### Behaviors
- Show field-level validation as the user edits.
- Save triggers non-destructive validation before persistence.
- If runtime reload succeeds, show a calm confirmation with effective timestamp.

### States
- Invalid config: field errors plus section summary.
- Runtime apply failure: keep edits visible and show retry/supporting guidance.

## Notification Center

### Goal
Centralize nudge delivery state across Codex, dashboard, and OS channels.

### Layout
- Summary row: unread count, failed deliveries, snoozed items, channel health.
- Main feed with channel chips and per-delivery receipts.
- Side panel for selected notification detail on large screens.

### Behaviors
- Mark read/unread, dismiss, snooze, retry failed delivery where supported.
- Group by nudge id with per-channel receipt drill-down.
- Global bell badge count matches unread notifications here.

### States
- No notifications yet: explain where first nudges will appear.
- Failed delivery cluster: call out OS permission or channel configuration issues.

## Responsive Rules
- Today and Focus collapse secondary panels beneath primary insights on mobile.
- Timeline filters move into a bottom sheet under `768px`.
- Reports switch from three columns to vertically stacked sections under `1024px`.
- Settings uses section accordions on mobile to prevent scroll fatigue.

## Cross-Screen Data Contracts
- `ActivityEvent` powers Timeline rows and Today activity preview.
- `ProjectSignal` powers Focus breakdowns and explanation copy.
- `FocusScore` powers Today hero, Focus chart, and Reports average score context.
- `Nudge` powers Drift Alerts and Notification Center.
- `CycleReport` powers Reports current and historical views.
- `TrackerConfig` powers Settings and affects explanatory UI copy across screens.

## Required System States
| State | Required treatment |
|---|---|
| Loading | skeletons, keep layout stable |
| Empty | explain next step and why data is missing |
| Error | preserve last known data when possible |
| Low confidence | show warning badge plus explanation |
| Offline/local | reassure that core behavior remains local-first |
