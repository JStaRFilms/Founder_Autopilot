# Builder Prompt

## Stack-Specific Instructions
- Backend runtime is a local Python daemon with SQLite persistence.
- Frontend is a local Next.js TypeScript dashboard consuming local APIs.
- No cloud dependencies are required for core v1 behavior.
- Privacy-first: never send activity payloads to external services by default.
- Notification integrations must support Codex inbox, dashboard center, and OS notifications.

## MUS Priority Order
1. FR-001: Local Activity Ingestion Daemon
2. FR-002: Canonical Event Normalization
3. FR-003: Focus Scoring Engine
4. FR-004: Nudge Decision Engine
5. FR-005: Multi-Channel Notification Delivery
6. FR-006: Dashboard Timeline and Metrics
7. FR-008: Tracker Configuration Controls
8. FR-007: Weekly Cycle Reports

## Special Considerations
- Optimize for single-user reliability over configurability breadth.
- Keep scoring/nudge logic explainable in UI and logs.
- Enforce strict boundaries against feature creep into team/cloud/mobile scope.
- Maintain interface compatibility with the six required contracts in `docs/Project_Requirements.md`.
