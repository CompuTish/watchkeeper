# The full variant, and why this one replaced it

Watchkeeper is the second design of the same idea. The first ran for 38 days,
from 2 October to 9 November 2026, on a real software product. It was larger,
it worked, and it taught nearly everything in [lessons](lessons.md). This page
describes it honestly, because some people will want parts of it back, and
because it is where the roadmap comes from.

## What the first design looked like

Some totals from that run, counted when it ended:

- between 7 and 15 lane agents registered at once, plus a coordinator;
- 8,723 headings in the shared log;
- 146 pull requests merged into the main branch over the period.

To keep that many agents moving, it grew machinery:

- **Separate records for everything.** Every work item, booking, lease,
  hand-back, and ruling had its own small JSON file, several thousand in all,
  alongside the log.
- **Leases.** Each use of an environment was a lease file with a hard release
  time, a snapshot of every other lane's status at the moment it was taken, and
  a receipt when it ended. Staging and production were booked separately.
- **Three layers of liveness.** A background event watcher, written in Python,
  produced snapshots of the log. An operating-system watchdog ran every 15
  minutes from the system scheduler, checked sessions, pipelines, deadlines,
  and disk space, and raised desktop notifications. A recurring prompt inside
  the coordinator's session carried a full state snapshot each time.
- **A locked writer.** Appends to the log went through a helper that held a
  file lock for long enough that guards could re-read and re-check state.
- **A backlog and a release tracker** inside the coordinator's own files.

## Why it was replaced

Mostly, the machinery cost more than it saved.

- The log grew to more than 11 megabytes, much of it routine traffic, and
  became hard for a person to read.
- The thousands of side files had to agree with the log and with each other,
  and keeping them in agreement became work in itself.
- The watchdog's picture of the world went stale. Its list of lanes was fixed
  when it was written, and by the end it reported little beyond low disk space.
- The background watcher crashed after running out of file handles, and
  nothing noticed for a while.
- Two separate environment bookings meant two sets of rules about how they
  interacted.

The second design kept the principles and threw away most of the parts:

| First design | Watchkeeper |
|---|---|
| Backlog and release tracker in the coordinator's files | An ordinary kanban board, one card per lane |
| Thousands of JSON side files | The log holds only the lock, decisions, and relayed rulings |
| Separate staging and production bookings, with lease files | One lock, expressed as posts plus line 1 of each status file |
| Event watcher, operating-system watchdog, and in-session prompts | One blocking reader plus the owner's watcher tick |

It turned out to be just as effective, and much easier to run, inspect, and
explain. Its own biggest lesson, that a parked lane can only be woken by a
person, isn't something more machinery would have fixed.

## Roadmap

These are the parts of the first design most likely to come back, as optional
extras, in roughly this order:

1. **A health check for the coordinator itself**, outside its session, so a
   dead coordinator is noticed even when the owner is away.
2. **An optional structured log**, with JSON Lines as the source and a
   generated Markdown view for people.
3. **Release and review gates**, which check that a review was done on the
   exact commit being released, in a fresh session, before anything reaches
   production.
4. **A decision record**, which logs every coordinator decision with its
   class, the evidence, and the rule it relied on, checked against the policy
   file.
5. **Adapters**, which let the coordinator start and resume lanes in specific
   agent tools directly, where the tool allows it.

None of these is needed to get started, and each will arrive only once it has
earned its place. If you need one of them sooner, open an issue and say why.
