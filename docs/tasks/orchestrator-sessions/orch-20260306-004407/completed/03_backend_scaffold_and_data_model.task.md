# 03 - Backend Scaffold and Data Model

## Agent Setup (DO THIS FIRST)
### Workflow to Follow
- Read Takomi workflow: `vibe-build.md`

### Prime Agent Context
- MANDATORY: run `vibe-primeAgent` first

### Required Skills
Load the following skills first, then scan for any additional relevant skills before executing.

| Skill | Why |
|---|---|
| takomi | Workflow and gate alignment |
| avoid-feature-creep | Prevent overbuilding backend beyond v1 local-first needs |

### Additional Skill Scan (MANDATORY)
- Check available skills list and include any directly relevant skill discovered during task analysis.
## Objective
Scaffold Python daemon service with SQLite and API/data contracts.

## Scope
- Python service structure and app entrypoints
- SQLite schema and migration system
- Config loader for watch scope, cadence, notification toggles
- Base API contract between daemon and dashboard

## Deliverables
- daemon skeleton
- SQLite schema and migration files
- config module and sample config

## Definition of Done
- Daemon starts locally
- Database initializes from migrations
- Config can be loaded and validated

## Acceptance Checklist
- [x] Backend scaffold created
- [x] Migration flow verified
- [x] Config loader implemented
- [x] Base contract documented


