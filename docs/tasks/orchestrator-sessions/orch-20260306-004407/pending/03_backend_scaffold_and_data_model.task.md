# 03 - Backend Scaffold and Data Model

## Agent Setup (DO THIS FIRST)
### Workflow to Follow
- Read Takomi workflow: `vibe-build.md`

### Prime Agent Context
- MANDATORY: run `vibe-primeAgent` first

### Required Skills
- takomi

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
- [ ] Backend scaffold created
- [ ] Migration flow verified
- [ ] Config loader implemented
- [ ] Base contract documented
