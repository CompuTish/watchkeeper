# Tools

Watchkeeper doesn't care which agent you use. Any agent that can read a file,
write a file, and run a shell command can be a lane or the coordinator. This
page gives a short recipe for each tool we know of, and says plainly whether it
has been tested.

Each tool's own documentation is the authority on its flags and limits, and
they change often. The commands below were checked against that documentation
on 25 November 2026. If something has moved, the documentation wins. Please
open an issue so we can fix this page.

## What every recipe needs

1. **Start the agent with its prompt.** The coordinator gets
   [templates/coordinator-prompt.md](../templates/coordinator-prompt.md), and
   each lane gets a filled-in [templates/lane-prompt.md](../templates/lane-prompt.md).
   Both include [templates/common-rules.md](../templates/common-rules.md).
2. **Let it reach the workspace.** The agent must be able to read and write
   `LOG.md`, `status/`, and `.watchkeeper/`, and run `wk`. If the tool
   sandboxes file writes, make sure the Watchkeeper directory is writable.
3. **Tell it who it is.** Set `WATCHKEEPER_AS` (for example
   `export WATCHKEEPER_AS=ALPHA`) and `WATCHKEEPER_DIR` in the shell the agent
   uses, or have it pass `--as` and `--dir` every time.
4. **Know how to resume it.** You are the wake-up mechanism for parked lanes
   (see [liveness](liveness.md)), so write down how to resume each lane before
   you need to.

## Status at a glance

| Tool | Role tried | Status |
|---|---|---|
| Claude Code (command line) | Coordinator | **Used in practice** |
| Codex CLI | Lanes | **Used in practice** |
| Claude desktop app (Code tab) | Either | Should work, untested |
| Codex desktop app (local mode) | Either | Should work, untested |
| Pi | Either | Should work, untested |
| OpenCode | Either | Should work, untested |
| Agents on local models | Either | Should work, untested |
| Anything else | Either | Plain-files fallback |

## Claude Code (used in practice, as the coordinator)

- **Start:** from the project directory, `claude "$(cat coordinator-prompt.md)"`
  starts an interactive session with the prompt as its first message.
- **Blocking reader:** Claude Code's foreground commands time out after a few
  minutes by default. A longer command is moved to the background rather than
  killed, and in an interactive session background commands have no time
  limit. Ask the coordinator to run `wk watch --as COORDINATOR --timeout 1500`
  as a background command and to act when it finishes.
- **Watcher tick:** `/loop 30m <the watcher tick prompt>` re-sends the prompt
  on a fixed interval within the session. Loops belong to the session, so start
  a new one after you resume.
- **Resume:** `claude --continue` resumes the most recent conversation in the
  current directory. `claude --resume <name or ID>` resumes a specific one.
  Background commands aren't restarted on resume, so the coordinator must start
  its reader again.

## Codex CLI (used in practice, for the lanes)

- **Start:** from the lane's working copy, `codex "$(cat lane-prompt.md)"`.
- **Sandbox:** `--sandbox workspace-write` lets the agent write inside its
  workspace. If the Watchkeeper directory is outside it, check your sandbox
  settings, or the lane won't be able to post.
- **Waiting:** a lane usually doesn't need a long blocking reader. It checks
  `wk read --as <LANE>` at each step, and acknowledges once it has acted. If it
  must wait, keep `wk watch` timeouts short (a few minutes) and loop. Codex
  documents a default polling window of about five minutes for background
  terminals.
- **Resume:** `codex resume --last` resumes the most recent session in the
  current directory. `codex resume <SESSION_ID>` resumes a specific one. Record
  each lane's session ID in its status file notes, so the owner can resume the
  right one.

## Claude desktop app (should work, untested)

The desktop app's Code tab runs Claude Code. In a local session it reads your
project, edits files, and runs commands, so the Claude Code recipe applies.
Sessions are listed in the sidebar for resuming. The chat side of the app,
outside the Code tab, can be given file access through local extensions but
doesn't run shell commands, so use the plain-files fallback there.

## Codex desktop app (should work, untested)

The Codex app's local mode works in your project directory on your own
computer, so a lane started there should be able to run `wk`. How to resume a
particular thread is not confirmed here. Please tell us what works.

## Pi (should work, untested)

- **Install:** see Pi's quickstart. At the time of writing:
  `npm install -g --ignore-scripts @earendil-works/pi-coding-agent`.
- **Start:** `pi @lane-prompt.md`. The `@path` form includes the file in the
  first message.
- **Tools:** Pi's default tools are `read`, `bash`, `edit`, and `write`. It
  doesn't ask before each tool call and has no built-in sandbox, so run it in a
  working copy you are happy for it to change.
- **Waiting:** a command timeout for `bash` is not documented, so keep
  `wk watch` timeouts short.
- **Resume:** `pi --continue`, or `pi --resume` to choose a session.

## OpenCode (should work, untested)

- **Start:** `opencode run "$(cat lane-prompt.md)"`.
- **Waiting:** OpenCode's shell tool times out after two minutes by default,
  and the timeout can be set per call. A command run in the background has no
  timeout unless one is given. Ask the agent to run `wk watch` in the
  background.
- **Resume:** `opencode run --continue "<message>"` continues the last session.
  `opencode run --session <ID> "<message>"` continues a specific one.

## Agents on local models (should work, untested)

Watchkeeper needs no network access and sends nothing anywhere, so it suits
local models well. The agent tool does the model plumbing:

- **Codex CLI** has an `--oss` mode with `--local-provider ollama` or
  `--local-provider lmstudio`.
- **Pi** reads custom providers from its `models.json`, including any
  OpenAI-compatible local server such as Ollama or LM Studio.
- **OpenCode** looks for a local Ollama server automatically, and can be
  pointed at other OpenAI-compatible servers.

Smaller models find exact formats harder. That is one reason `wk post` writes
the heading itself and refuses a malformed one, rather than trusting the agent
to type it. If a model keeps getting refused, give it the protocol page and the
example log from the toy project.

## Plain-files fallback

No agent tool at all? Any agent that can read and append to a text file can
follow the protocol by hand:

1. Read `LOG.md` from the line you last acknowledged. Keep that line number
   somewhere durable.
2. To post, append a heading, a body, and the end marker, in one write, with
   the time from `date -u +%Y-%m-%dT%H:%M:%SZ`.
3. To take the environment, check that every other status file's line 1 says
   `NONE` and that your latest coordinator post is your `ENTRY OPEN`, then
   rewrite your own line 1.

Run `wk lint` (or ask someone to) from time to time, to catch mistakes.

## Reporting back

If you try Watchkeeper with any of these, please open an issue saying which
tool, which role, and what happened, good or bad. The "untested" labels will
change only on real reports.
