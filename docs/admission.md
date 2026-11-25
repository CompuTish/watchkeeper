# Admission

Admission is how a lane gets the shared environment and how it gives it back.
It is the heart of the protocol, and every rule on this page exists because
its absence caused a real problem.

## The sequence

```text
lane         REQUEST            "I'm ready. Here's what I'll change and how to undo it."
coordinator  ADMITTED           "You're queued. Agreed steps, expected state, rollback."
coordinator  ENTRY OPEN         "Go now. Operation OP-0001, window 18:05Z-18:35Z."
lane         (status line 1 → OP-0001)
lane         ENTERED            "I hold the lock. The expected state was there."
             ...the lane works; HOLD, GO, and WAIT as needed...
lane         (status line 1 → NONE)
lane         RELEASED           "Done, cleaned up, nothing left behind."
coordinator  ACCEPTED+RELEASED  "I've checked it myself. Case closed. Next lane."
```

One lock covers staging and production together. Running two lanes in one
environment while a third is in the other sounds efficient, but it multiplies
the ways two changes can interfere, and in practice one lock was simpler and
just as fast.

## Admitting in advance

The coordinator may admit a lane well before its turn. `ADMITTED` agrees the
steps, the state the lane should expect to find, and the rollback. That way the
lane is ready to move the moment the environment frees up. Admission isn't
permission, though. Only `ENTRY OPEN` is.

## The entry trigger is exact

```text
## COORDINATOR → ALPHA: ENTRY OPEN — OP-0001 — 18:05Z-18:35Z — 2030-01-07T18:03:10Z
```

Lanes look for that exact heading: `ENTRY OPEN`, then the operation ID, then
the window as `HH:MMZ-HH:MMZ`. The coordinator must never paraphrase it. "Entry
is open", "OK to go", or "you're clear" all look like permission to a person,
and a lane matching the exact form will rightly ignore them. `wk lint` rejects
near-misses such as `OPEN ENTRY` or `ENTRY-OPEN`, and rejects the phrase inside
any other post's heading.

Two things never grant entry:

- **The clock.** Reaching the start of a window isn't permission.
- **Another lane's release.** "BETA has released, so I'll go" is exactly the
  race the lock exists to prevent.

## The latest post binds

While a lane's case is open, its authority is **the most recent coordinator
post addressed to it, or to all lanes**. If that post is its `ENTRY OPEN`, it
may enter. If anything else has been posted to it since, even a harmless
all-lanes housekeeping note, the lane must not enter, because its binding post
is no longer an entry trigger.

That sounds strict, and it is. The alternative is lanes guessing which earlier
post still counts, and guessing is how two lanes end up in one environment. So
the rule for the coordinator is: **while a lane's case is open, post nothing
else to it or to all lanes.** If you must, re-post the full `ADMITTED` or
`ENTRY OPEN` afterwards. `wk post` refuses a `NOTE`, `QUESTION`, or `RULING`
from the coordinator in that situation, unless you add `--force`. Decisions
about the case itself (`GO`, `WAIT`, `HOLD`, and `WITHDRAWN`) are allowed,
because they are meant to change the lane's authority.

`wk status set` enforces the entry side: it takes the lock only if the lane's
binding post is `ENTRY OPEN` for that exact operation.

## Predecessor binding

Every `ENTRY OPEN` (or the `ADMITTED` before it) names the exact state the lane
must find before it changes anything. That might be which version is deployed,
which build is live, or a count that should be zero. If the lane finds anything
else, it posts `HOLD` before touching the environment.

After each release, the coordinator works out the predecessor state for the
next lane and says which earlier changes the next deploy will replace. A lane
that deploys over an unexpected state is how a fix that worked on staging
quietly disappears.

## Withdrawing an unused slot

If a lane hasn't entered a few minutes into its window, the coordinator
withdraws the slot explicitly:

```text
## COORDINATOR → ALPHA: WITHDRAWN — OP-0001 — not entered, slot reassigned — 2030-01-07T18:12:00Z
```

Before withdrawing, check that the lane really hasn't started: read its status
file, the log, and the list of running deploys. Then give the slot to a lane
that is awake and ready, and re-queue the sleeper. An idle environment held for
a lane that has gone quiet is the commonest waste in the whole system.

## The coordinator checks before it closes

`RELEASED` is the lane's claim. `ACCEPTED+RELEASED` is the coordinator's
verdict, and it comes only after the coordinator has looked for itself, using
read-only checks: the deploy finished on the expected commit, the data the lane
created has been cleaned up, and nothing unexpected was left behind. A
successful response code proves that something happened. It does not prove
that the outcome you wanted holds.

## When things go wrong

- **A lane posts `HOLD`.** The coordinator classifies before ruling (see
  [lessons](lessons.md)). Was it a product fault, a test-tooling fault, or a
  check looking in the wrong place? The ruling names its class and the
  evidence.
- **Infrastructure flakes.** Settle before retrying: check whether the thing
  actually started, approve exactly one retry after a short pause, and treat a
  second failure as a `HOLD`.
- **A dependency slips.** Re-plan in one post to every affected lane, and ask
  each to acknowledge it.

Next: [decision rights](decision-rights.md).
