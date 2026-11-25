# Liveness

Liveness is the question "what makes the next thing happen?" An agent waiting
on a file does nothing until something wakes it. A coordinator that nobody
wakes is no coordinator at all. This page explains the two wake sources
Watchkeeper uses, and the third one that turned out to matter most: you.

## Two independent wake sources

**1. A blocking reader in the coordinator's session.** The coordinator runs:

```sh
wk watch --as COORDINATOR --timeout 1500
```

This waits, for up to 25 minutes, until a lane posts. Then it prints the new
posts and exits, which hands control back to the coordinator. The coordinator
deals with them, acknowledges them (`wk read --as COORDINATOR --ack`), and
starts the reader again. Until they are acknowledged, the reader returns at
once with the same posts marked `REDELIVERED`, so forgetting to acknowledge
shows up straight away rather than hiding a post. On timeout, the reader lists any lane that has been
quiet for two hours or more. `bin/watch.sh` does the same in plain shell.

Keep **exactly one** reader running. Two readers race, and an orphaned reader
from an old session wakes nobody.

**2. The owner's watcher tick.** On a schedule, every 15 to 60 minutes
depending on how busy things are, the owner (or a scheduler acting for them)
sends the coordinator one fixed prompt. The prompt is in
[templates/watcher-tick.md](../templates/watcher-tick.md). It tells the
coordinator to:

1. read the log from its cursor;
2. sweep the chat channels and email it is responsible for;
3. draft any replies, and send none;
4. record anything that changed in the owner's notes;
5. make sure exactly one blocking reader is running;
6. never print a secret;
7. do nothing visible if nothing has changed.

That is the whole scheduler. It works because the two sources fail
differently. The reader wakes the coordinator when a lane posts, but not when
the world changes elsewhere. The tick wakes it when nothing has been posted,
and catches a reader that died.

## The owner is the wake-up mechanism

This is the lesson that surprised us most. Many agent harnesses let an agent
pursue a goal over many turns. If an agent is blocked for several turns in a
row on something outside its control, such as waiting for its slot, it parks
itself and stops. **The coordinator can't wake a parked lane. Only a person
can.** Posting `ADMITTED` or `ENTRY OPEN` to a parked lane does nothing,
because nobody is reading.

In practice this meant a shared environment sitting idle for hours while the
lane holding the slot was asleep, and several lanes parked behind one slow
upstream lane. The fixes are simple, and they are the coordinator's job:

- Put every "please resume this lane" request at the **top** of the owner
  update, with exactly what to resume and how.
- Batch the requests, and ask again after about 20 minutes if nothing happens.
- Notify the owner when the environment is idle or a critical path is blocked.
- Never hold a slot open for a sleeping lane. Give it to an awake one and
  re-queue the sleeper.
- When an upstream lane lands, tell the owner exactly which parked lanes to
  resume, and in what order.

## Keeping the session healthy

- Long sessions get their context compacted or summarised. After that, the
  coordinator re-reads its prompt, the log from its cursor, and the status
  files. It never relies on its memory of earlier turns.
- Check free disk space on every pass. Each lane usually has its own working
  copy and dependencies, and they add up quickly.
- Don't compute expiry times for credentials or sign-ins. Ask the tool that
  issued them. A guessed expiry is how a release fails in the middle of the
  night.
- Write a handover before the session ends (see
  [templates/handover.md](../templates/handover.md)), so a fresh coordinator
  can resume from the files alone.

Next: [working with the outside world](working-with-the-outside-world.md).
