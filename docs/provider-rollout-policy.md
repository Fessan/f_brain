# Provider Rollout Policy

## Decision Date

- 2026-02-17

## Current Production Default

- Default provider: `claude-cli`
- Reason: current integration path is battle-tested in project workflows (`/process`, `/do`, `/weekly`) and has lower operational uncertainty before full credentialed matrix completion.

## Fallback Strategy

- Fallback mode: **manual operational switch**, not automatic in runtime.
- Reason: automatic failover can create split-brain behavior between providers and make incidents harder to diagnose.

## Promotion Criteria for `openai`

`openai` may become default only after all are true:

1. Credentialed E2E matrix (`task-018`) is complete for P1-P12.
2. Failure scenarios N1-N7 are validated with predictable safe behavior.
3. No high-severity regressions in vault writes, Todoist actions, or Telegram output.
4. Closed-contour Docker runtime remains stable during canary period.

## Provider Switch Procedure

1. Edit `.env`:
   - `LLM_PROVIDER=openai`
   - `OPENAI_API_KEY=<real key>`
   - `OPENAI_MODEL=<approved model>`
2. Restart services:
   - `make restart`
3. Verify:
   - `make ps`
   - `make logs-bot`
   - `make logs-scheduler`

## Emergency Rollback Procedure

1. Edit `.env`:
   - `LLM_PROVIDER=claude-cli`
2. Restart services:
   - `make restart`
3. Confirm stable bot startup and scheduler health:
   - `make ps`
   - `make logs`

## Operational Notes

- Keep both provider credentials configured in secure environments when possible, but only one provider active via `LLM_PROVIDER`.
- Any provider switch must be followed by smoke checks for `/process`, `/do`, `/weekly`.
