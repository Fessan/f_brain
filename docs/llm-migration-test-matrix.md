# LLM Migration Test Matrix

This document defines acceptance checks for migration from a single-provider
runtime to provider-routed architecture.

## Scope

- Providers: `claude-cli`, `openai`
- Flows:
  - `/process`
  - `/do` (text + voice)
  - `/weekly`
  - automation scripts (`scripts/process_daily.py`, `scripts/weekly.py`)
- Non-functional:
  - output safety and formatting
  - failure handling and observability
  - behavior parity for core capabilities

## Pre-Run Checklist

1. Configure `.env` for target provider.
2. Ensure vault paths exist and contain test fixtures.
3. Ensure Telegram bot token and allowed user ID are valid for test chat.
4. Ensure Todoist token is valid for integration tests.

## Core Scenario Matrix

| ID | Provider | Flow | Type | Expected Result |
|----|----------|------|------|-----------------|
| P1 | claude-cli | `/process` with daily note entries | Positive | Returns HTML report, creates expected vault updates, commit/push path still works |
| P2 | openai | `/process` with daily note entries | Positive | Same behavioral outcome as P1 (report + vault updates), no capability drift |
| P3 | claude-cli | `/do` text request requiring Todoist + file ops | Positive | Executes tools and returns Telegram-safe report |
| P4 | openai | `/do` text request requiring Todoist + file ops | Positive | Same result class as P3, no unsupported capability errors |
| P5 | claude-cli | `/do` via voice | Positive | Voice transcribed, request executed, report returned |
| P6 | openai | `/do` via voice | Positive | Same as P5 with provider parity |
| P7 | claude-cli | `/weekly` | Positive | Digest generated, summary persisted in vault, MOC updated |
| P8 | openai | `/weekly` | Positive | Same as P7 with provider parity |
| P9 | claude-cli | `scripts/process_daily.py` | Positive | Runs end-to-end and sends formatted report |
| P10 | openai | `scripts/process_daily.py` | Positive | Runs end-to-end with same output contract |
| P11 | claude-cli | `scripts/weekly.py` | Positive | Runs end-to-end and sends formatted report |
| P12 | openai | `scripts/weekly.py` | Positive | Runs end-to-end with same output contract |

## Failure-Mode Matrix

| ID | Category | Injection Method | Expected Result |
|----|----------|------------------|-----------------|
| N1 | Tool error | Force Todoist API failure (invalid token) | Structured error in response envelope, Telegram-safe error output, no crash |
| N2 | Timeout | Artificially low provider timeout | Request fails fast with explicit timeout error |
| N3 | Malformed model output | Return invalid HTML from provider | Formatter escapes/sanitizes output, message still sendable |
| N4 | Partial capabilities | Disable one capability (e.g. `vault.write_file`) | Clear unsupported-capability error, no silent success |
| N5 | Provider unavailable | Missing CLI binary / invalid OpenAI endpoint | Startup/runtime failure is explicit and actionable |
| N6 | Git failure | Reject push (no remote/network) | Processing report still delivered; git failure logged and isolated |
| N7 | Session context corruption | Malformed JSONL line in `.sessions` | Parser skips bad line and continues without crash |

## Concurrency/Responsiveness Checks

| ID | Scenario | Expected Result |
|----|----------|-----------------|
| C1 | Long-running `/process` while bot receives new updates | Event loop remains responsive due handler threading strategy |
| C2 | Two sequential long `/do` requests | No deadlock, status updates continue, both responses complete |

## Output Contract Checks

1. Response envelope fields exist for all use-case outputs:
   - `report` or `error`
   - `provider`
   - `processed_entries`
   - `timings`
2. Handler compatibility:
   - legacy dict conversion still works for formatter.
3. Telegram constraints:
   - only allowed tags survive sanitization
   - oversized output is truncated safely

## Acceptance Gates

Migration phase is accepted only if:

1. All positive scenarios P1-P12 pass.
2. All failure scenarios N1-N7 fail safely and predictably.
3. Concurrency checks C1-C2 show no event-loop starvation.
4. Output contract checks pass in both provider modes.
5. No unresolved high-severity regressions in vault writes or Todoist actions.

## Suggested Execution Order

1. Run claude-cli positive suite.
2. Run openai positive suite.
3. Run failure-mode suite for each provider.
4. Run concurrency checks.
5. Run final smoke suite on scripts and bot commands.
