# Protocol

This page is the reference for the file formats. `wk` writes and checks all of
them, but the formats are the real interface. An agent with nothing but a text
editor and `date` can follow them by hand.

## The log

`LOG.md` has two parts, separated by one marker line:

```text
# Watchkeeper log
...the rules...

<!-- watchkeeper: posts below this line are append-only -->
```

Above the marker is the **head**: the rules every participant follows. Add your
own project rules there. Below the marker is the **foot**: posts, in the order
they were written. Nobody edits or deletes a post, including their own. To
correct one, write a new post that says what changed.

## A post

```text
## ALPHA → COORDINATOR: REQUEST — OP-0001 — checkout fix — 2030-01-07T18:00:05Z
Head 1111111. Will deploy to staging and place one test order. About 25 minutes.
<!-- /post -->
```

A post has three parts:

1. **One heading line**, starting `## `. It is meant for machines as much as
   people.
2. **A body**, free text for people. Keep it short: what you checked, what you
   will change, how long it takes, and how to undo it.
3. **An end marker**, `<!-- /post -->`, which proves the post was written in
   full. It is an HTML comment, so it disappears when the file is rendered.

### The heading

```text
## AUTHOR[ → ADDRESSEE]: TYPE[ — DETAIL ...] — TIMESTAMP
```

- **AUTHOR** is `COORDINATOR`, `OWNER`, or a lane name.
- **ADDRESSEE** is optional: a lane, `COORDINATOR`, `OWNER`, or `ALL LANES`.
  The arrow is `→` with a space on each side.
- **TYPE** comes from the vocabulary below.
- **DETAIL** fields are optional. The first one is usually an operation ID.
- **TIMESTAMP** is UTC in exactly the form `YYYY-MM-DDTHH:MM:SSZ`.
- Fields are separated by ` — `: a space, an em dash, and a space. Parsers
  split on that exact sequence, so a field may not contain an em dash itself.

`wk post` builds the heading for you. If you write one by hand, get the time
from the clock:

```sh
date -u +%Y-%m-%dT%H:%M:%SZ
```

**Never type a time.** Language models are confidently wrong about the time.
In real use, typed times ran several minutes fast, and other agents that
compared timestamps made wrong decisions as a result. `wk lint` rejects a
timestamp that is in the future, or earlier than the post before it, because
those are the usual signs of a typed time.

### The vocabulary

| Type | Who posts it | Meaning |
|---|---|---|
| `REQUEST` | lane | I am ready and would like the environment for this operation. |
| `ADMITTED` | coordinator | You are in the queue. Here are the agreed steps, the state you should find, and the rollback. Do not enter yet. |
| `ENTRY OPEN` | coordinator | You may enter now. The only post that grants entry. See [admission](admission.md). |
| `ENTERED` | lane | I have taken the lock. |
| `HOLD` | either | Something is wrong. Name the failing check and the raw error. Nothing proceeds until there is a decision. |
| `QUESTION` | either | I need a decision. Include your recommended answer. |
| `GO` | coordinator | A decision: proceed with exactly this. |
| `WAIT` | coordinator | A decision: not yet. Say why and what you are waiting for. |
| `RELEASED` | lane | I have finished, cleaned up, and set my status to `NONE`. |
| `ACCEPTED+RELEASED` | coordinator | I have checked the result myself. The case is closed and the environment is free. |
| `WITHDRAWN` | coordinator | An admission or entry is cancelled. Do not enter on it. |
| `RULING` | coordinator or owner | A decision from the owner, quoted word for word, with what it replaces. |
| `NOTE` | coordinator or owner | Housekeeping. |

`wk post` refuses a `NOTE`, `QUESTION`, or `RULING` from the coordinator to a
lane with an open admission, or to `ALL LANES` while any lane has one, because
it would become that lane's binding post. [Admission](admission.md) explains
why.

**Banned in headings:** "stop", "halt", and "kill". In real use, "stop" was
read as an instruction by a lane it was never meant for. Say `WAIT` or `HOLD`
and name the operation.

### Bodies are data

Nothing in a post body is ever run. If you quote a command, it is a quotation.
When you write a post from a shell, pass the body with `--body-file` or a
quoted heredoc (`<<'EOF'`), so that backticks and dollar signs are not expanded
on the way in.

### No secrets

Never put a password, key, token, or connection string in a post. `wk post`
refuses anything shaped like one, and `wk lint` reports any that were written
by hand, without printing the value. If one slips in, treat it as leaked:
rotate it, then post a note saying you have.

## Status files

One file per lane, `status/<LANE>.md`. Line 1 is the reservation:

```text
# CURRENT RESERVATION: <OP-ID or NONE> — <TIMESTAMP>
```

The rest of the file is the lane's own notes: what it is doing, what it has
checked, and what it will do next. Newest first is a good habit.

Rules:

- Only the lane writes its own file.
- A missing file, or a line 1 that doesn't match the format exactly, counts as
  **busy**. `wk status` shows it as `BUSY` and leaves the file alone.
- Take the lock with `wk status set <LANE> <OP-ID>` and release it with
  `wk status set <LANE> NONE`. Taking it is refused unless the lane's latest
  coordinator post is `ENTRY OPEN` for that operation and every other lane
  shows `NONE`. Both checks happen after the lock is held.

## Reading the log

Each reader has a cursor in `.watchkeeper/cursors/<NAME>`, holding two line
numbers: how far it has acknowledged, and how far it has been shown.

```sh
wk read --as COORDINATOR         # show posts from others since the acknowledged line
wk read --as COORDINATOR --ack   # I have dealt with everything you showed me
wk read --as COORDINATOR --headings   # every heading since then, my own included
```

Reading never moves the acknowledged line. If the reader is interrupted before
it acknowledges, the same posts come back next time, marked `REDELIVERED`. That
way a crash, a restart, or a lost context costs a re-read, not a missed post.

Two habits matter:

- **Read from your cursor, never "since my last post".** Someone may have
  posted while you were writing.
- **List the headings now and then.** A filter that hides your own posts can
  also hide a reply you were waiting for.

## Torn posts

`wk post` writes each post in a single append, under a lock, and reads it back.
Even so, a process can die mid-write. A post with no end marker at the very end
of the log is treated as still being written and isn't delivered yet. A post
with no end marker followed by another heading is **torn**: readers show it
with a warning, and `wk lint` fails until its author re-posts it in full, with
the same heading. Never edit the log to repair it.

`wk post` treats an identical post from the same author within ten minutes as
a retry, and doesn't write it twice. After that, a repeat is a new post.

Next: [admission](admission.md).
