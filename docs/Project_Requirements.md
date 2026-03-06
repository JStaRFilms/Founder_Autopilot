# Project Requirements Document

## Project Overview

**Name:** Founder Autopilot v1  
**Mission:** Help a solo founder protect deep work by turning local activity into clear focus/drift feedback and actionable nudges.  
**Tech Stack:** Python daemon, SQLite, Next.js dashboard (TypeScript), OS notifications

## Problem Statement
Solo founders lose momentum when context switching, low-signal work, and unnoticed drift compound over days. Existing tools either require cloud data sharing, manual journaling, or heavyweight team workflows. Founder Autopilot v1 provides local-first, automatic activity tracking and concise coaching loops designed for one person.

## Product Goals (v1)
1. Capture meaningful founder activity from local sources with minimal setup.
2. Classify activity into focus vs. drift signals and compute a daily focus score.
3. Deliver timely, non-intrusive nudges in three channels (Codex inbox, dashboard, OS).
4. Produce cycle reports that help the founder adjust weekly behavior.

## Non-Goals (v1 Scope Boundaries)
- Multi-user collaboration, teams, shared workspaces.
- Cloud sync, remote telemetry, or SaaS backend.
- Financial analytics, CRM, or full project management replacement.
- AI autonomous task execution; only recommendations and nudges.
- Mobile app; web dashboard + local notifications only.

## Target User
- **Primary user:** a single technical or non-technical solo founder working mostly on one local machine.
- **Usage mode:** local-first, privacy-preserving, no mandatory internet dependency for core workflows.

## Functional Requirements

| FR ID | Description | User Story | Status |
| :--- | :--- | :--- | :--- |
| FR-001 | Local activity ingestion daemon | As a founder, I want the system to collect activity events from Git, COS, and configured folders automatically so that I do not manually log work. | MUS |
| FR-002 | Canonical event normalization | As a founder, I want all captured activities converted into a consistent event schema so that downstream scoring and reporting remain reliable. | MUS |
| FR-003 | Focus scoring engine | As a founder, I want daily and rolling focus scores computed from my activity signals so that I can quantify deep work versus drift. | MUS |
| FR-004 | Nudge decision engine | As a founder, I want context-aware nudges generated when my activity indicates drift, stagnation, or over-fragmentation so that I can course-correct quickly. | MUS |
| FR-005 | Multi-channel notification delivery | As a founder, I want nudges delivered to Codex inbox, dashboard notification center, and OS notifications so that I reliably see guidance where I already work. | MUS |
| FR-006 | Dashboard timeline and metrics | As a founder, I want a dashboard that shows events, focus score trends, and active nudges so that I can inspect what happened and why. | MUS |
| FR-007 | Weekly cycle reports | As a founder, I want cycle reports summarizing wins, drift patterns, and next actions so that I can run lightweight weekly reviews. | MUS |
| FR-008 | Tracker configuration controls | As a founder, I want to configure watch paths, signal weighting, quiet hours, and nudge aggressiveness so that the system matches my workflow. | MUS |
| FR-009 | Smart categorization presets | As a founder, I want optional presets for classifying common startup work modes so that setup time is faster. | Future |
| FR-010 | Export and archive reports | As a founder, I want to export cycle reports to markdown/JSON so that I can archive progress externally. | Future |

## Required Interface Definitions

### ActivityEvent
```ts
interface ActivityEvent {
  id: string;
  source: 'git' | 'cos' | 'filesystem' | 'manual';
  timestamp: string; // ISO-8601
  actor: 'founder';
  projectId: string;
  signalType: 'code' | 'writing' | 'planning' | 'research' | 'ops' | 'unknown';
  summary: string;
  metadata: Record<string, string | number | boolean | null>;
}
```

### ProjectSignal
```ts
interface ProjectSignal {
  id: string;
  projectId: string;
  windowStart: string; // ISO-8601
  windowEnd: string; // ISO-8601
  focusMinutes: number;
  driftMinutes: number;
  contextSwitchCount: number;
  confidence: number; // 0..1
  derivedFromEventIds: string[];
}
```

### FocusScore
```ts
interface FocusScore {
  id: string;
  projectId: string;
  date: string; // YYYY-MM-DD
  score: number; // 0..100
  trend: 'up' | 'flat' | 'down';
  contributingSignals: Array<{
    signal: string;
    weight: number;
    impact: number;
  }>;
  computedAt: string; // ISO-8601
}
```

### Nudge
```ts
interface Nudge {
  id: string;
  createdAt: string; // ISO-8601
  type: 'focus' | 'break' | 'prioritize' | 'review';
  severity: 'low' | 'medium' | 'high';
  title: string;
  message: string;
  reason: string;
  targetChannels: Array<'codex' | 'dashboard' | 'os'>;
  status: 'pending' | 'delivered' | 'dismissed' | 'snoozed';
}
```

### CycleReport
```ts
interface CycleReport {
  id: string;
  projectId: string;
  periodStart: string; // ISO-8601
  periodEnd: string; // ISO-8601
  averageFocusScore: number;
  topWins: string[];
  driftPatterns: string[];
  recommendedActions: string[];
  generatedAt: string; // ISO-8601
}
```

### TrackerConfig
```ts
interface TrackerConfig {
  projectId: string;
  watchPaths: string[];
  excludedPaths: string[];
  signalWeights: Record<string, number>;
  quietHours: {
    start: string; // HH:mm
    end: string; // HH:mm
    timezone: string;
  };
  nudgeSensitivity: 'low' | 'medium' | 'high';
  notificationChannels: Array<'codex' | 'dashboard' | 'os'>;
}
```

## Quality & Acceptance Standards
- All MUS features must function offline after initial setup.
- Every FR must have objective acceptance criteria and a dedicated issue file.
- Data should be retained locally in SQLite and readable through documented schemas.
- Nudge generation must be explainable (reason text included with every nudge).

## Release Readiness Definition (v1)
Founder Autopilot v1 is release-ready when FR-001 through FR-008 are complete, validated by issue acceptance criteria, and exercised end-to-end from local event ingestion to weekly cycle report generation.
