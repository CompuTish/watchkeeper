# Watchkeeper

**A lane coordinator for AI agents.**

In the Royal Navy, the officer of the watch keeps the ship running while the
captain sleeps. Watchkeeper is that idea applied to AI agents. You, the owner,
are mostly absent. Several agents work in parallel, each on its own piece of
work. One more agent, the coordinator, keeps watch: it decides who goes next,
stops two agents from deploying over each other, and wakes you only for the
decisions that are genuinely yours.

There is no server, no database, and no framework. Watchkeeper is a protocol
written down in plain Markdown files, plus a small command that keeps those
files honest. Any agent that can read a file, write a file, and run a shell
command can take part.

> **Status: first release.** This is a starting kit, not a finished product. It
> is deliberately small, and it will grow over the coming days and weeks.
> Reports of what works and what doesn't are very welcome.

## Who it is for

- People with big plans and small teams, who want several agents working at
  once without the agents tripping over each other.
- Anyone running local models, or trying to get more out of one or two AI
  subscriptions.
- Any role: product managers, engineers, executives, or someone keeping a busy
  life in order. You need a couple of hours' familiarity with the command line,
  and no more.

## The idea in five minutes

| Word | What it means |
|---|---|
| **Owner** | You. You set the goals and keep the decisions that matter: anything outward-facing, anything touching customer data, money, credentials, or a production release. |
| **Lane** | One agent working on one piece of work, such as "fix the checkout total". Lanes have short upper-case names like `ALPHA`. |
| **Coordinator** | One agent that reads everything the lanes say, decides the order, and holds the line on safety. It never does a lane's work for it. |
| **Board** | Any kanban tool you like. One card is one lane. Watchkeeper doesn't integrate with it. People and agents update it. |
| **Log** | One shared Markdown file. The top holds the rules. Below a marker line, posts are only ever appended. |
| **Lock** | One shared environment (staging and production together) that only one lane may use at a time. |
| **Status file** | One small file per lane. Its first line says what that lane holds right now. |
| **Cursor** | A bookmark in the log for each reader. It moves only when the reader says "done", so nothing is skipped after a crash. |
| **Watcher tick** | A short, fixed prompt you send the coordinator on a schedule, so it wakes even when nobody has posted. |

A lane that wants the environment posts a `REQUEST`. The coordinator replies
`ADMITTED`, and later `ENTRY OPEN` with an operation ID and a time window. Only
then may the lane take the lock, by writing its status file. When it finishes,
it posts `RELEASED`. The coordinator checks the result for itself and closes
the case with `ACCEPTED+RELEASED`. Then the next lane goes.

The coordinator drafts messages to customers and colleagues but never sends
them. Anything that leaves the building goes through you.

## Quickstart

You need Python 3.10 or later and a POSIX shell: macOS, Linux, or Windows
Subsystem for Linux. Native Windows isn't supported. Nothing else is
installed.

```sh
git clone https://github.com/CompuTish/watchkeeper
cd watchkeeper
export PATH="$PWD/bin:$PATH"
wk --version
```

Watch a whole run, two lanes and a coordinator, replay in about a second:

```sh
examples/toy-project/replay.sh
```

The script narrates each step, including the moments where Watchkeeper refuses
something. At the end it prints where it left the log, so you can read it.

Now try it yourself in a scratch directory:

```sh
cd "$(mktemp -d)"
wk init --lanes ALPHA,BETA
wk post --as ALPHA --to COORDINATOR REQUEST OP-0001 "checkout fix" --body "About 20 minutes on staging."
wk read --as COORDINATOR
wk read --as COORDINATOR --ack
wk post --as COORDINATOR --to ALPHA ADMITTED OP-0001
wk post --as COORDINATOR --to ALPHA "ENTRY OPEN" OP-0001 14:00Z-14:30Z
wk status set ALPHA OP-0001
wk status
wk lint
```

To run the tests, from the repository folder:
`python3 -m unittest discover -s tests -t tests`.

If you'd rather have `wk` installed than on your `PATH`, run
`pip install git+https://github.com/CompuTish/watchkeeper` inside a virtual
environment. Watchkeeper is not published on the Python Package Index.

## The commands

| Command | What it does |
|---|---|
| `wk init --lanes A,B` | Creates `LOG.md` with the rules at the top, a status file per lane, and a `.watchkeeper/` folder for cursors. |
| `wk post --as WHO [--to WHO] TYPE [DETAIL ...]` | Appends one post. It stamps the time from the clock, checks the vocabulary, refuses anything that looks like a secret, holds a lock while writing, reads the post back, and quietly ignores an exact retry. |
| `wk read --as WHO` | Shows posts from others since your cursor. Nothing moves until you run `wk read --as WHO --ack`. |
| `wk watch --as WHO` | Waits (25 minutes by default) for a post from someone else, then shows it. On timeout it lists lanes that have gone quiet. |
| `wk lint` | Checks every heading, timestamp, end marker, and status file, and looks for secrets. |
| `wk status [set LANE OP-ID\|NONE]` | Shows who holds the environment, or takes or releases it. Taking it needs an `ENTRY OPEN` for that exact operation and every other lane showing `NONE`, both checked after the lock is held. |

`bin/watch.sh` does the same job as `wk watch` in plain POSIX shell, for
machines without Python. The two share cursor files.

## Works with

Watchkeeper is plain files and one command, so any agent that can read and
write files and run a command can be a lane or the coordinator. Here is what
has actually been tried.

| Tool | Status |
|---|---|
| Claude Code as the coordinator, Codex CLI as the lanes | **Used in practice.** This is the combination the design was built and run on. |
| Claude and Codex desktop apps (where they can run local commands), Pi, OpenCode, and agents backed by local models | **Should work, untested.** See [docs/tools.md](docs/tools.md) for a short recipe for each. Please report how it goes. |
| Anything else | **Plain-files fallback.** All you need is a file, a terminal, and the protocol. |

## Read next

The docs are in teaching order. Each builds on the one before.

1. [Concepts](docs/concepts.md): the cast and the props.
2. [Protocol](docs/protocol.md): the log format, the vocabulary, and status line 1.
3. [Admission](docs/admission.md): how a lane gets the environment, and how it gives it back.
4. [Decision rights](docs/decision-rights.md): what the coordinator may decide, written down as data.
5. [Liveness](docs/liveness.md): who wakes whom, and why you are part of the answer.
6. [Working with the outside world](docs/working-with-the-outside-world.md): chat, email, and drafts.
7. [Lessons](docs/lessons.md): what went wrong in real use, and the rule each failure produced.
8. [Tools](docs/tools.md): recipes for each agent harness.
9. [The full variant](docs/v2-full-variant.md): the larger first design, and why this one replaced it.

The [templates](templates/) folder has the prompts: coordinator, lane, common
rules, watcher tick, owner update, handover, and review.

## Where this came from

The design was worked out in daily use, coordinating many agents on a real
software product. The first version ran for more than five weeks and grew a lot
of machinery. This second version keeps the principles and drops most of the
machinery. It turned out to be just as effective and much easier to live with.
[The full variant](docs/v2-full-variant.md) tells that story.

## Licence

MIT. See [LICENSE](LICENSE).
