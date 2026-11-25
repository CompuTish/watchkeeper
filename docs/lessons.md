# Lessons

Every rule in Watchkeeper exists because something went wrong without it. This
page lists those failures, generalised, with the rule each one produced. Where
a rule is enforced by `wk` or checked by a test, it says so.

The incidents come from the two designs described in
[the full variant](v2-full-variant.md). The details have been made generic, but
the shape of each failure is real.

## The log and its language

**A lock check that looked at some lanes, not all of them.** It read two
status files out of seven and declared the environment free. *Rule: the lock
check reads every registered lane, and a lane it can't read counts as busy.*
(`wk status set`. Tests T1 and T2.)

**A malformed status line in someone else's file.** A guard refused to proceed
because another lane's header had drifted into a slightly different format.
The temptation was to "fix" the other lane's file. *Rule: shared file formats
are interfaces. Validate them, treat unreadable as busy, and never edit
another lane's file.* (Test T2.)

**A word in a heading read as an instruction.** "Stop" in a heading was taken
as a halt by a lane it wasn't addressed to. A control word placed mid-heading
was missed by a lane looking for it at the start. *Rule: a controlled
vocabulary, fixed positions, and banned words.* (`wk lint`. Test T4.)

**Typed times.** Agents wrote timestamps from what they believed the time to
be, and were up to a quarter of an hour out. Other agents compared those times
and made wrong calls. *Rule: every time comes from the clock.* (`wk post`
stamps it, and `wk lint` rejects future or out-of-order times. Test T5.)

**A quietly edited heading.** A heading another lane had pinned was corrected
in place, and the pin broke. *Rule: the foot is append-only. Correct by
posting again.*

**A post body run as a command.** Backticks in a body written through an
unquoted shell heredoc were executed. *Rule: bodies are data. Write them from a
file or a quoted heredoc.*

**A secret in a post.** A connection string in URL form slipped past a mask
that only looked for `password=`. *Rule: refuse anything shaped like a secret,
in every form, and parse rather than mask.* (`wk post` and `wk lint`. Test T19.)

## Reading and waking

**A watcher that printed headings only.** A `HOLD` sat unread for nearly an
hour because the body, which said what was wrong, was never shown. *Rule:
deliver every body since the last acknowledgement.* (Test T6.)

**A cursor that moved when it printed.** The reader advanced its bookmark as
soon as it showed new posts. When the coordinator was interrupted before
acting, those posts were never seen again. *Rule: the cursor moves only on
acknowledgement.* (`wk read --ack`. Tests T7 and T27.)

**Reading "since my last post".** A coordinator set its bookmark after writing
its own post, and skipped a lane's question that arrived in between. It
happened six times. *Rule: read from a cursor. Posting never moves it.*

**A post delivered twice.** After a restart, the same instruction was
delivered again. *Rule: redelivered posts are marked as such, and a retried
post is not written twice.* (Test T25.)

**A post cut short.** A writer died mid-append. *Rule: every post has an end
marker. An unfinished post is not delivered, and a torn one is flagged.*
(Test T26.)

**Admission mistaken for a wake-up.** A lane admitted in advance sat idle for
40 minutes because nothing told it that its turn had come. *Rule: entry needs
an explicit `ENTRY OPEN`, and the owner must resume a parked lane.*

**Parked lanes.** Lanes that had parked themselves couldn't be woken by any
post. The environment sat idle while the lane holding the slot slept. *Rule:
the owner is the wake-up mechanism. Resume requests go at the top of the owner
update, and slots go to lanes that are awake.* (See [liveness](liveness.md).)

**Watchers that multiplied.** Duplicate and orphaned readers from old sessions
raced or woke nobody. *Rule: exactly one reader, started by the coordinator's
own harness.*

## Deciding

**Workers stalled on questions.** Before there was a coordinator, agents with
only a lock waited hours for a human. *Rule: give one agent written authority,
with an explicit list of what it may not decide.* (See
[decision rights](decision-rights.md).)

**Ruling before classifying.** Most failures in one busy day were checks
looking in the wrong place, not product faults: a security check that tested
the wrong leg of a connection, a test that couldn't find a table whose
headers lacked the right attributes, a screenshot taken before the page had
settled. *Rule: classify before you rule. Is it the product, the test, or the
infrastructure?*

**Conditions that couldn't be met.** The coordinator asked a lane to prove
that some tests had run in a pipeline that, by design, never ran them. *Rule:
withdraw your own condition when it proves impossible, and say what evidence
you will accept instead.*

**Asking permission for routine retries.** Lanes queued for a ruling on every
fix to their own test tooling. *Rule: a standing allowance of a few local
retries that touch only the lane's own tooling. Product changes still need a
ruling.*

**Blind retries after an infrastructure error.** A deploy request timed out
and nothing appeared. Retrying at once risks running it twice. *Rule: settle
first. Check whether it started, allow exactly one retry after a short pause,
and treat a second failure as a `HOLD`.*

**A dependency slipped.** The plan said one lane would land first and another
would build on it. When the first failed, the order had to flip. *Rule:
re-plan in one post to every affected lane, and ask each to acknowledge it.*

**Rigour out of proportion.** Verification tooling became the critical path,
and releases waited on flaky checks rather than real faults. *Rule:
proportionate rigour. Never weaken an assertion about the product, never let
test tooling block a release on its own, and simplify after repeated tooling
failures.*

## Evidence

**A success code hiding a failure.** A request returned success while the
email it should have triggered never arrived. *Rule: prove the durable
outcome, not the response code.*

**Approval without inspection.** A result was accepted on a lane's word.
*Rule: the coordinator checks for itself, read-only, before
`ACCEPTED+RELEASED`, and records what it looked at.*

**A check that couldn't fail.** A verification passed because the list it
checked was empty. *Rule: every negative check has a positive control, and
every "all of these" check first proves there is at least one.*

**Facts from memory.** Identities, addresses, dates, and expiry times were
recalled instead of looked up, and were wrong. *Rule: query the system that
knows.*

## The outside world

**A paraphrased answer.** A colleague's reply was summarised, and the summary
said something they hadn't. *Rule: relay rulings word for word.*

**A future-dated sweep.** A chat sweep used a lower bound in the future and
missed a message for 20 minutes. *Rule: compute sweep bounds from the clock.*

**A reply in the wrong thread.** *Rule: reply in the thread of the person's own
latest message.*

**A guessed address.** *Rule: use only confirmed addresses.*

**Anything outward-facing.** *Rule: draft, never send.*

## The machine itself

**Full disks.** Each lane's working copy and dependencies took gigabytes.
*Rule: check free space on every pass.*

**Evidence in a temporary folder.** It was cleaned away. *Rule: keep evidence
somewhere durable.*

**Sleep and power.** A laptop going to sleep stops every agent on it. *Rule:
power and sleep are part of liveness.*

**Shared working copies.** Agents sharing one checkout switched each other's
branches. *Rule: one branch and one working copy per lane. Never add every
file in bulk, and never restore a stash you didn't make.*
