# 04 - Event Ingestion (Git, COS, File Watch)

## Agent Setup (DO THIS FIRST)
### Workflow to Follow
- Read Takomi workflow: `vibe-build.md`

### Prime Agent Context
- MANDATORY: run `vibe-primeAgent` first

### Required Skills
Load the following skills first, then scan for any additional relevant skills before executing.

| Skill | Why |
|---|---|
| takomi | Controlled execution flow |
| security-audit | Ensure ingestion logic avoids unsafe command/file handling patterns |

### Additional Skill Scan (MANDATORY)
- Check available skills list and include any directly relevant skill discovered during task analysis.
## Objective
Implement event ingestion for Git, COS, and focused folder activity.

## Scope
- Source adapters for each event source
- Dedupe logic
- Source attribution
- Timestamp normalization
- Storage into unified event table

## Deliverables
- ingestion adapters/workers
- normalization and dedupe modules
- tests for ordering and dedupe correctness

## Definition of Done
- Events from all 3 sources are captured
- Duplicates are suppressed
- Timestamps are normalized consistently

## Acceptance Checklist
- [ ] Git adapter works
- [ ] COS adapter works
- [ ] File watch adapter works
- [ ] Dedupe and ordering tests pass


