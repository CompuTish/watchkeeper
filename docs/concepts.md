# Concepts

This page introduces the cast and the props. The other pages assume you have
read it.

## Why a lock is not enough

Picture two agents sharing one staging environment. The obvious fix is a lock:
whoever holds it may deploy, and the other waits. That works until the first
agent hits a question it can't answer. Is this test failure a real bug or a
flaky check? May I retry? Should I give up and let the other one go first?

With only a lock, the agent either guesses or stops and waits for a human, who
is asleep. Both are bad. What the agents need is someone with written authority
to make routine decisions, and a reliable place to hear them. That is the
coordinator and the log.

## The cast

**The owner** is the person in charge, usually you. The owner sets goals,
writes down what the coordinator may decide alone, and keeps the decisions that
should never be delegated: anything sent to customers or colleagues, anything
touching customer data, credentials, billing, or a new production release. The
owner is often absent, and the design assumes it.

**A lane** is one agent working on one piece of work. It has a short upper-case
name (`ALPHA`, `CHECKOUT`, `NOTIFICATIONS`), its own branch and working copy,
and a written brief called the lane prompt. A lane does its own work, tests
locally first, and asks for the shared environment only when it is ready.

**The coordinator** is one more agent whose job is the big picture. It reads
everything the lanes post, decides the order in which they use the shared
environment, rules on routine questions, checks results for itself, and
escalates to the owner only what is genuinely the owner's. It doesn't write the
lanes' code. Detail belongs to the lanes. Sequencing, unblocking, and the
consequences one lane's work has for another belong to the coordinator.

## The props

**The board** is any kanban tool. One card is one lane. Cards move as lanes
post, and only the coordinator or the owner marks a card done, after checking
the real outcome in production. Each pull request names its card, and the card
records the pull request's link and the exact commit it was tested at.
Watchkeeper doesn't connect to the board. That is deliberate: the board is for
people, and it works with whatever tool you already use.

**The log** is one shared Markdown file, `LOG.md`. The top part, the head,
holds the rules. Below a marker line, the foot, posts are appended and never
edited. The log is for three things only: the environment lock, the
coordinator's decisions, and rulings from the owner, relayed word for word.
Progress reports belong on the board, and working notes belong in each lane's
status file. Keeping the log narrow keeps it readable.

**The lock** covers the shared environments, staging and production together.
Only one lane holds it at a time. Taking it involves a short exchange of posts,
described in [admission](admission.md), and a change to the lane's status file.

**A status file** is one small Markdown file per lane, in `status/`. Its first
line is a machine-readable statement of what the lane holds:

```text
# CURRENT RESERVATION: OP-0001 — 2030-01-07T18:05:02Z
```

or `NONE` when it holds nothing. Everything below line 1 is the lane's own
notes. Only the lane writes its own file. A first line that can't be read
counts as busy, because wrongly assuming "free" is the expensive mistake.

**A cursor** is a bookmark in the log for one reader. It records how far the
reader has got and, separately, how far it has acknowledged. It moves only on
acknowledgement, so a reader that crashes after seeing a post, but before
acting on it, sees that post again.

**The watcher tick** is a short, fixed prompt the owner sends the coordinator
on a schedule. It tells the coordinator to read the log, sweep chat and email,
draft any replies, record what changed, and make sure exactly one blocking
reader is running. If nothing has changed, it does nothing visible. See
[liveness](liveness.md).

## What Watchkeeper is not

- It is not an agent framework. It doesn't start agents, call models, or hold
  conversations. You run the agents however you like.
- It is not a scheduler. Time never grants permission to do anything.
- It is not a chat system. The log is a record of decisions, not a place to
  think aloud.

Next: [the protocol](protocol.md).
