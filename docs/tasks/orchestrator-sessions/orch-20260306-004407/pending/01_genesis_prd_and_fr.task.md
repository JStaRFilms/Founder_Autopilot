# 01 - Genesis PRD and FR

## Agent Setup (DO THIS FIRST)
### Workflow to Follow
- Read Takomi workflow: `vibe-genesis.md`

### Prime Agent Context
- MANDATORY: run `vibe-primeAgent` first

### Required Skills
Load the following skills first, then scan for any additional relevant skills before executing.

| Skill | Why |
|---|---|
| takomi | Core workflow routing and lifecycle protocol |
| avoid-feature-creep | Keep MUS scope tight and explicit |
| spawn-task | Produce implementation-ready FR issue breakdowns |

### Additional Skill Scan (MANDATORY)
- Check available skills list and include any directly relevant skill discovered during task analysis.
## Objective
Produce complete product blueprints for Founder Autopilot v1.

## Scope
- Project requirements and mission clarity
- Functional requirements inventory (MUS + Future)
- Detailed issue files with testable acceptance criteria
- Required interfaces:
  - ActivityEvent
  - ProjectSignal
  - FocusScore
  - Nudge
  - CycleReport
  - TrackerConfig

## Deliverables
- `docs/Project_Requirements.md`
- `docs/issues/FR-*.md`
- `docs/Builder_Prompt.md` (if special instructions are needed)

## Definition of Done
- PRD exists and is complete
- Every FR has one issue file
- Acceptance criteria are objective and testable
- All 6 required interfaces are defined

## Acceptance Checklist
- [ ] PRD committed
- [ ] FR issue files committed
- [ ] Interface definitions included in spec
- [ ] Scope boundaries documented


