# Founder Autopilot Design System

## Purpose
Founder Autopilot is a local-first coaching dashboard for one founder. The UI should feel calm, exact, and slightly editorial: less "analytics command center", more "private operations desk". Every major screen must answer three questions fast:

1. What is my current focus quality?
2. Why did it change?
3. What should I do next?

## Product IA

### Primary navigation
| Area | Goal | Primary objects |
|---|---|---|
| Today | Daily status and next best action | focus score, current streak, top drift reasons, live timeline |
| Timeline | Audit activity and context switches | events, source filters, date range, explanation drawer |
| Focus | Inspect score drivers and deep-work patterns | trend charts, signal breakdowns, confidence, recommendations |
| Drift Alerts | Review nudges and intervention history | active nudges, cooldowns, dismiss/snooze actions |
| Reports | Run weekly review loops | cycle reports, wins, drift patterns, action items |
| Settings | Configure tracker and coaching rules | watch paths, exclusions, weights, quiet hours, channels |
| Notification Center | Triage all delivered notifications | Codex, dashboard, OS receipts, unread state, delivery failures |

### Global layout
- Desktop: left rail navigation, top utility bar, right contextual panel on dense screens.
- Tablet: collapsible left rail, top utility bar, stacked content.
- Mobile: top app bar, bottom sheet filters, single-column content, sticky key action.

### Global utility zones
- Left rail: app identity, nav, local-first status, weekly focus average.
- Top bar: date scope, project selector, quick search, keyboard shortcut hint, notification bell.
- Context panel: explanation, raw signal details, action preview, help copy.

## Brand Direction

### Design concept
`Quiet Ops Room`

The interface is built around paper-light surfaces, dark ink typography, measured spacing, and restrained signal color. Positive momentum uses moss and teal. Drift uses amber and rust, not alarming red by default. Surfaces feel tactile and private.

### Personality keywords
- calm
- rigorous
- private
- grounded
- explainable
- anti-hype

### Anti-patterns
- glossy SaaS gradients
- neon status overload
- dense unreadable data tables
- decorative charts without interpretation
- alerts that look like failures when they are only coaching cues

## Visual Tokens

### Color palette
| Token | Hex | Usage |
|---|---|---|
| `bg.canvas` | `#F4F1EA` | app background |
| `bg.surface` | `#FBF8F2` | cards, panels |
| `bg.surfaceStrong` | `#F0E8DC` | selected cards, sticky summaries |
| `bg.inverse` | `#161616` | dark overlays, command surfaces |
| `fg.primary` | `#1E2321` | headings, core body text |
| `fg.secondary` | `#4C5A55` | supporting copy |
| `fg.tertiary` | `#6F7C76` | metadata |
| `border.soft` | `#D9D1C5` | default border |
| `border.strong` | `#B9AEA0` | active border |
| `accent.focus` | `#1F6B5C` | focus-positive states |
| `accent.focusSoft` | `#D7EEE7` | focus pills, fills |
| `accent.drift` | `#C46A2D` | drift and warning states |
| `accent.driftSoft` | `#F7E2D2` | drift pills, warning fills |
| `accent.info` | `#355C7D` | neutral data emphasis |
| `accent.infoSoft` | `#DCE6EF` | information fills |
| `accent.critical` | `#A2472E` | high-severity delivery failure |
| `accent.criticalSoft` | `#F5D8D0` | critical fills |

### Semantic state rules
- Success means sustained focus, completed report actions, or healthy delivery status.
- Warning means drift risk, fragmented context, or low-confidence scoring.
- Critical is reserved for delivery failures, invalid settings, or broken ingestion.
- Never rely on color alone; every state pairs with iconography and text.

### Typography
| Role | Token | Spec |
|---|---|---|
| Display | `type.display` | `"Fraunces", Georgia, serif`, 600, tight tracking |
| Heading | `type.heading` | `"IBM Plex Sans", "Segoe UI", sans-serif`, 600 |
| Body | `type.body` | `"IBM Plex Sans", "Segoe UI", sans-serif`, 400/500 |
| Data | `type.mono` | `"IBM Plex Mono", "Cascadia Code", monospace`, tabular |

### Type scale
| Token | Size / Line height | Use |
|---|---|---|
| `display.l` | `56 / 60` | page hero value on Today |
| `display.m` | `44 / 48` | report score header |
| `h1` | `32 / 38` | screen titles |
| `h2` | `24 / 30` | section titles |
| `h3` | `18 / 24` | card titles |
| `body.l` | `16 / 24` | default body |
| `body.s` | `14 / 20` | metadata, helper text |
| `label` | `12 / 16` | pill labels, control captions |

### Spacing scale
| Token | Value |
|---|---|
| `space.1` | `4px` |
| `space.2` | `8px` |
| `space.3` | `12px` |
| `space.4` | `16px` |
| `space.5` | `20px` |
| `space.6` | `24px` |
| `space.8` | `32px` |
| `space.10` | `40px` |
| `space.12` | `48px` |
| `space.16` | `64px` |

### Radius and elevation
| Token | Value | Use |
|---|---|---|
| `radius.sm` | `8px` | chips, inputs |
| `radius.md` | `14px` | cards |
| `radius.lg` | `20px` | large panels |
| `radius.xl` | `28px` | hero cards |
| `shadow.soft` | `0 8px 24px rgba(22, 22, 22, 0.06)` | default elevation |
| `shadow.raised` | `0 18px 40px rgba(22, 22, 22, 0.10)` | overlays |

## Motion
- Default transitions: `160ms ease-out`.
- Screen transitions: subtle opacity and 12px upward settle.
- Hover: color, border, or shadow change only. No layout-shifting scale on cards.
- Timeline/live indicators may pulse at low amplitude; provide reduced-motion fallback.
- Respect `prefers-reduced-motion` by removing pulse, chart shimmer, and staggered entrances.

## Grid and Responsiveness

### Breakpoints
| Token | Width |
|---|---|
| `sm` | `375px` |
| `md` | `768px` |
| `lg` | `1024px` |
| `xl` | `1440px` |

### Layout rules
- `sm`: single column, filters in sheets, charts stacked above tables.
- `md`: two-column content zones, nav collapses into icon rail.
- `lg`: full rail + content + optional context pane.
- `xl`: preserve whitespace; do not stretch content past readable line lengths.

## Navigation Rules
- Include a visible skip link before navigation.
- Active nav item uses left border bar plus filled background, not color only.
- Notification Center is utility-first but still first-class in navigation because FR-005 is MUS.
- Badge counts cap at `99+`.
- Global search should return events, nudges, reports, and settings sections.

## Component Inventory

### Score cards
- Variants: daily focus, rolling average, context switches, confidence.
- Anatomy: label, main value, delta, one-sentence explanation, optional sparkline.
- Minimum width: `240px`.
- Use mono numerals for values.

### Trend chart panel
- Primary chart: line chart for daily focus over time.
- Supporting overlays: drift minutes area fill, confidence band, optional target threshold.
- Include legend toggles and textual summary above chart.

### Timeline row
- Anatomy: time, source badge, signal type, summary, metadata strip, explanation affordance.
- Group by hour or session block on dense days.
- Expand state reveals raw metadata and scoring impact.

### Alert / nudge card
- Variants: focus, break, prioritize, review.
- Anatomy: severity badge, title, message, reason, channels, status, actions.
- Actions: dismiss, snooze, open related screen.
- Severity color does not replace reason text.

### Filter bar
- Controls: date range, source, signal type, severity, project, confidence threshold.
- Desktop: inline segmented + popover controls.
- Mobile: sticky compact bar opening bottom sheet.

### Settings form
- Group by domain: tracking, scoring, quiet hours, channels.
- Every section includes plain-language help copy and validation state.
- Use inline validation and non-destructive previews where possible.

### Notification widget
- Variants: unread stack, delivery health, channel breakdown, recent failures.
- Widget cards appear on Today and full Notification Center.

### Report panel
- Sections: average score, wins, drift patterns, recommended actions, historical comparison.
- Recommended action rows must support check-off state in future implementation.

## Interaction Patterns
- Explanations are always one click away from any computed metric.
- Empty states should coach next setup step instead of merely reporting missing data.
- Bulk actions only appear where batching is common: notification triage, event labeling.
- Destructive actions require confirmation if they permanently dismiss or clear history.

## Accessibility Rules
- Minimum text contrast: 4.5:1 for body text, 3:1 for large type.
- Keyboard tab order must match visual order.
- Focus ring token: `2px` outline using `accent.info` with `2px` offset.
- Provide visible skip link on every screen.
- Charts require textual summaries and legends that do not depend on color alone.
- Notification live regions must be polite; do not interrupt screen readers for low-severity updates.

## Content Guidelines
- Keep labels plain and operational: "Drift Alerts", not "Attention Engine".
- Explanations are specific and causal: "Three context switches in 28 minutes reduced confidence."
- Use short sentence case labels.
- Avoid motivational fluff. The product should read like a good operator, not a coach bot.

## Engineering Handoff Notes
- For Next.js implementation, self-host fonts with `next/font`.
- Prefer CSS variables matching the tokens above.
- Use SVG icons from a single set such as Lucide.
- Preserve local-first cues in the UI: sync state, last scan time, offline-safe copy.
