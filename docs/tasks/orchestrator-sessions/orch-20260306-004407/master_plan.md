# Founder Autopilot - Orchestrator Master Plan

Session ID: orch-20260306-004407
Created: 2026-03-06 00:44:07
Root: docs/tasks/orchestrator-sessions/orch-20260306-004407

## Goal
Deliver Founder Autopilot v1 as a local-first system that tracks founder activity (Git + COS + focused folders), computes focus/drift, and sends nudges to Codex inbox, dashboard notification center, and OS notifications.

## Stack
- Backend: Python daemon
- Storage: SQLite
- Frontend: Next.js dashboard

## Hard Constraints
- Single-user founder mode only
- Local-first only, no cloud sync
- Focused watch scope only
- Approval gate between dependent phases

## Task Registry
| # | File | Mode | Workflow(s) | Depends On | Status |
|---|------|------|-------------|------------|--------|
| 1 | 01_genesis_prd_and_fr.task.md | vibe-architect | vibe-genesis | - | completed |
| 2 | 02_design_system_and_dashboard_spec.task.md | vibe-architect | vibe-design | 1 | pending |
| 3 | 03_backend_scaffold_and_data_model.task.md | vibe-code | vibe-build | 1 | completed |
| 4 | 04_event_ingestion_git_cos_files.task.md | vibe-code | vibe-build | 3 | completed |
| 5 | 05_scoring_scheduler_and_reports.task.md | mode-code | mode-code | 4 | completed |
| 6 | 06_dashboard_ui_and_settings.task.md | vibe-code | vibe-build | 2,5 | pending |
| 7 | 07_notifications_codex_dashboard_os.task.md | mode-code | mode-code | 5,6 | pending |
| 8 | 08_review_finalize_docs.task.md | vibe-review | mode-review, vibe-finalize, vibe-syncDocs | 1-7 | pending |

## Review Gates
- Gate A (after 1): PRD + FRs accepted
- Gate B (after 2): Design system accepted
- Gate C (after 5): backend core accepted
- Gate D (after 7): integration accepted
- Gate E (after 8): final signoff

## Progress Checklist
- [x] Gate A passed
- [ ] Gate B passed
- [ ] Gate C passed
- [ ] Gate D passed
- [ ] Gate E passed

## Promotion Rule
A task file moves from `pending/` -> `in-progress/` -> `completed/` only when its acceptance checklist is fully passed and dependency gates are satisfied.
