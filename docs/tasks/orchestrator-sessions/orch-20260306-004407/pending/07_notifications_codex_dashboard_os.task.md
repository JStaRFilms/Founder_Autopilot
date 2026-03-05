# 07 - Notifications (Codex, Dashboard, OS)

## Agent Setup (DO THIS FIRST)
### Workflow to Follow
- Read Takomi workflow: `mode-code.md`

### Prime Agent Context
- MANDATORY: run `vibe-primeAgent` first

### Required Skills
- takomi

## Objective
Implement nudge delivery routing across all v1 channels.

## Scope
- Codex inbox message adapter
- Dashboard notification center adapter
- System notification adapter
- Channel toggles and fallback/error handling

## Deliverables
- notification routing layer
- per-channel adapters
- fallback and retry behavior

## Definition of Done
- Nudge can fan out to enabled channels
- Channel failures degrade gracefully
- User channel settings are respected

## Acceptance Checklist
- [ ] Codex channel works
- [ ] Dashboard channel works
- [ ] OS notification channel works
- [ ] Fallback/error handling verified
