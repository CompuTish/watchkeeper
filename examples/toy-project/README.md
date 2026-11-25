# Toy project: two lanes, one environment

This example replays a short, fictional run in a fresh directory:

```sh
examples/toy-project/replay.sh            # in a new temporary directory
examples/toy-project/replay.sh ./my-run   # or somewhere you choose
```

Nothing touches a real system. The "deploys" and "checks" are sentences in
post bodies. What is real is the log, the status files, and every refusal.

## The story

Two lanes share one staging environment:

- **ALPHA** is fixing a checkout total.
- **BETA** is adding a report to a nightly batch job.

| Step | What happens | What it teaches |
|---|---|---|
| 1 | The owner runs `wk init --lanes ALPHA,BETA`. | The log, status files, and cursors. |
| 2 | Both lanes post `REQUEST`. | Say what you'll change, how long it takes, and how to undo it. |
| 3 | The coordinator reads, then acknowledges. | The cursor moves only on acknowledgement. |
| 4 | ALPHA is `ADMITTED`, and BETA is told to `WAIT`. | Admission is not permission. |
| 5 | A housekeeping `NOTE` to all lanes is **refused**. | The latest post binds: a note would replace ALPHA's authority. |
| 6 | BETA tries to take the lock and is **refused**. | Entry needs your own `ENTRY OPEN`. |
| 7 | The coordinator posts `ENTRY OPEN — OP-0001 — 18:05Z-18:35Z`. | The trigger has one exact form. |
| 8 | ALPHA checks the expected state, takes the lock, and posts `ENTERED`. | Predecessor binding. |
| 9 | ALPHA's check fails, and it posts `HOLD` with the failing check. | A hold names its cause and proposes a fix. |
| 10 | The coordinator classifies it as a test fault and posts `GO` for one re-run. | Classify before you rule. |
| 11 | ALPHA passes, cleans up, releases, and reports. | Leave nothing behind. |
| 12 | The coordinator checks for itself, then posts `ACCEPTED+RELEASED`. | The coordinator verifies before it closes. |
| 13 | BETA is admitted, entered, and released in turn. | The next lane is woken explicitly. |
| 14 | `wk status` and `wk lint` show a free environment and a clean log. | |

## What the log looks like

An excerpt, with the times replaced by fictional ones:

```text
## ALPHA → COORDINATOR: REQUEST — OP-0001 — checkout total fix — 2030-01-07T18:00:05Z
Head 1111111. Will deploy to staging and place one test order. About 25 minutes. Rollback: staging revision 41.
<!-- /post -->

## COORDINATOR → ALPHA: ADMITTED — OP-0001 — queued 1 — 2030-01-07T18:03:10Z
Predecessor: staging serving revision 41, zero test orders. Steps as requested. Wait for ENTRY OPEN.
<!-- /post -->

## COORDINATOR → ALPHA: ENTRY OPEN — OP-0001 — 18:05Z-18:35Z — 2030-01-07T18:04:40Z
Find staging on revision 41 with zero test orders before you deploy. If not, HOLD.
<!-- /post -->

## ALPHA → COORDINATOR: HOLD — OP-0001 — confirmation check matched two elements — 2030-01-07T18:14:31Z
Deploy worked (revision 42). The test looks for the confirmation text and finds it twice: once in the panel, once in the header. One test order exists. Proposal: narrow the check to the panel and re-run once. I will not retry without a disposition.
<!-- /post -->
```
