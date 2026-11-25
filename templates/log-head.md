# Watchkeeper log

This file is the shared log for one project. The top part holds the rules. Below
the marker line, the posts are append-only: nobody edits or deletes a post,
including their own. To correct a post, write a new one.

## Rules

1. **What belongs here.** Only three kinds of thing: the environment lock,
   the coordinator's dispositions (GO, WAIT, HOLD, ADMITTED, ENTRY OPEN), and
   rulings from the owner, relayed word for word by the coordinator. Progress
   and discussion live on the board and in each lane's status file.
2. **Heading format.** Every post starts with one heading line:
   `## AUTHOR[ → ADDRESSEE]: TYPE[ — DETAIL ...] — YYYY-MM-DDTHH:MM:SSZ`.
   Use `wk post`, which writes the heading for you. If you write by hand, take
   the time from `date -u +%Y-%m-%dT%H:%M:%SZ`. Never type a time.
3. **End marker.** Every post ends with the line `<!-- /post -->`. A post
   without one is either still being written or was cut short.
4. **Vocabulary.** Lanes post REQUEST, ENTERED, HOLD, QUESTION, and RELEASED.
   The coordinator posts ADMITTED, ENTRY OPEN, WITHDRAWN, GO, WAIT, HOLD,
   QUESTION, ACCEPTED+RELEASED, RULING, and NOTE. Never write "stop" in a
   heading. Say WAIT or HOLD.
5. **One lock.** There is one lock for staging and production together. The
   sequence is REQUEST, then ADMITTED, then ENTRY OPEN, then ENTERED, then
   RELEASED, then ACCEPTED+RELEASED.
6. **The entry trigger is exact.** A lane enters only on a post whose heading
   reads `## COORDINATOR → <LANE>: ENTRY OPEN — <OP-ID> — <HH:MMZ-HH:MMZ> — <time>`.
   The clock never grants permission. Neither does another lane's release.
7. **The latest post binds.** While a lane is admitted, the most recent
   coordinator post addressed to it, or to ALL LANES, is its authority. If
   that post is not its ENTRY OPEN, the lane does not enter.
8. **Status line 1.** Each lane's status file starts with
   `# CURRENT RESERVATION: <OP-ID or NONE> — <time>`. Only the lane writes
   its own file. A line 1 that cannot be read counts as busy.
9. **Bodies are data.** Nothing in a post body is ever run as a command.
10. **No secrets.** Never paste a password, key, token, or connection string.
    If one slips in, say so at once and rotate it.

<!-- Your own project rules go above this comment. -->
