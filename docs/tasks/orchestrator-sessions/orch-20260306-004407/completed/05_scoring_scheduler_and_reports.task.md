# 05 - Scoring, Scheduler, and Reports

## Agent Setup (DO THIS FIRST)
### Workflow to Follow
- Read Takomi workflow: `mode-code.md`

### Prime Agent Context
- MANDATORY: run `vibe-primeAgent` first

### Required Skills
Load the following skills first, then scan for any additional relevant skills before executing.

| Skill | Why |
|---|---|
| takomi | Phase discipline and reporting cadence |
| avoid-feature-creep | Keep scoring/reporting simple and actionable for v1 |

### Additional Skill Scan (MANDATORY)
- Check available skills list and include any directly relevant skill discovered during task analysis.
## Objective
Build focus/drift scoring, 3x-daily scheduler, and report generation.

## Scope
- Score models for momentum, drift, and overload
- Default cadence and custom overrides
- Daily summary generation
- Two-week cycle report generation

## Deliverables
- scoring engine modules
- schedule engine modules
- report generation modules

## Definition of Done
- Scores compute from ingested events
- Scheduler supports default and custom cadence
- Reports generate with expected sections

## Acceptance Checklist
- [x] Scoring engine implemented
- [x] Scheduler implemented
- [x] Daily report generated
- [x] Cycle report generated


