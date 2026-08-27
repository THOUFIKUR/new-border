# BorderPulse Antigravity Project Package

## Upload/use order

1. `01_MASTER_PROJECT_SPECIFICATION.pdf`
2. `02_UI_UX_FIGMA_STITCH_HANDOFF.pdf`
3. `03_SYSTEM_VALIDATION_AND_TEST_PLAN.pdf`
4. `ANTIGRAVITY_MASTER_IMPLEMENTATION_PROMPT.md`
5. `CLAUDE_ARCHITECTURE_REVIEW.md` when asking Claude for review
6. `PROJECT_STATE.md` for continuation between chats

## Connected services

- Stitch/Figma: visual source of truth
- Supabase: database/storage source of truth
- Antigravity: primary implementation and testing agent
- Claude: architecture reviewer

## Important

Do not upload database passwords or service-role secrets into prompts.

Antigravity should use its already-authenticated Supabase connector.

The exact ESP32 pin map must be verified against the physical board before wiring because earlier project notes contain both classic ESP32 and ESP32-S3 provisional mappings.

## First prototype

Windows laptop + laptop camera + YOLO + polygon zone + ESP32 buzzer + Supabase.

Radar and ground sensors are simulated until physically available.
