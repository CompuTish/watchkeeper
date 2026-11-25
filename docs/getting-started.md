# Getting started on your own project

The quickstart in the README shows the moving parts. This page takes you from
an empty folder to a coordinator and two lanes working on your own project.
Allow an hour the first time, most of it spent writing prompts.

Start small: one coordinator, two lanes, and low-risk work, such as two
independent fixes that only ever reach a test environment. Widen it once you
have watched a few cycles go round.

## 1. Make `wk` available

Clone the repository somewhere permanent and put its `bin` folder on your
`PATH`, in your shell profile so that every agent's shell picks it up:

```sh
git clone https://github.com/CompuTish/watchkeeper ~/tools/watchkeeper
echo 'export PATH="$HOME/tools/watchkeeper/bin:$PATH"' >> ~/.profile
```

Use `~/.zshrc` instead of `~/.profile` if your shell is zsh.

## 2. Create a workspace

The workspace holds the log, the status files, and the cursors. Put it in its
own folder, **outside** the code repositories your lanes work in, so that no
lane commits it by accident. Every agent must be able to read and write it.

```sh
mkdir -p ~/coordination/my-project && cd ~/coordination/my-project
wk init --lanes CHECKOUT,NOTIFICATIONS
```

Name lanes after their work, in upper case. You can add a lane later by adding
its name to `.watchkeeper/lanes` and running `wk status set <LANE> NONE` once
to create its status file. That command is the one exception to "only the lane
writes its own file", because the file doesn't exist yet.

If you want a history of the coordination itself, make the workspace a private
Git repository of its own. Never make it public: it will describe your work in
detail.

## 3. Decide what the coordinator may decide

Copy the example policy into the workspace and read every line:

```sh
cp ~/tools/watchkeeper/templates/policy.example.yaml policy.yaml
```

The example is conservative on purpose. Anything outward-facing, anything
touching customer data, credentials, or billing, and every production approval
start with you. Read [decision rights](decision-rights.md) before you widen it.

Then add your own project rules to the head of `LOG.md`, above the line that
says your own rules go there. Good first rules name your environments, the
commands that deploy to them, and anything no lane may ever touch.

## 4. Write the prompts

Copy the templates and fill in every bracketed part:

```sh
mkdir -p prompts
cp ~/tools/watchkeeper/templates/coordinator-prompt.md prompts/coordinator.md
cp ~/tools/watchkeeper/templates/lane-prompt.md prompts/CHECKOUT.md
cp ~/tools/watchkeeper/templates/lane-prompt.md prompts/NOTIFICATIONS.md
```

- Paste [templates/common-rules.md](../templates/common-rules.md) where each
  prompt asks for it.
- In each lane prompt, the sections that matter most are "Why you exist", the
  deliverables, and "Done means". A lane with a vague goal will do vague work.
- In the coordinator prompt, list the lanes and point it at `policy.yaml` and
  a notes file for you, such as `owner-notes.md` in the workspace.

## 5. Start the coordinator

Open a terminal, set who it is and where the workspace is, and start your
agent tool from there with the coordinator prompt. [Tools](tools.md) has the
exact command for each tool.

```sh
cd ~/coordination/my-project
export WATCHKEEPER_AS=COORDINATOR WATCHKEEPER_DIR="$PWD"
```

Its first job is to start one blocking reader in the background:
`wk watch --as COORDINATOR --timeout 1500`.

## 6. Start each lane

Give each lane its own branch and working copy, so that lanes never share a
checkout. For example, with Git worktrees:

```sh
cd ~/code/my-app
git worktree add ../my-app-checkout -b fix/checkout-total
cd ../my-app-checkout
export WATCHKEEPER_AS=CHECKOUT WATCHKEEPER_DIR=~/coordination/my-project
```

Then start your agent tool there with the lane's prompt. Repeat in a new
terminal for each lane. If your tool sandboxes file writes, make sure the
workspace folder is writable from the lane's working copy.

## 7. Schedule the watcher tick

The watcher tick is what wakes the coordinator when nobody has posted. Send it
the prompt in [templates/watcher-tick.md](../templates/watcher-tick.md) every
15 minutes while lanes are busy and hourly when things are quiet. Some agent
tools can repeat a prompt on a schedule within a session. Otherwise, send it
yourself.

## 8. Your part

You are still in charge. Day to day, that means:

- **Read the owner update**, which starts with anything that needs you.
- **Resume parked lanes** when asked. Only you can, and the update tells you
  which ones, in what order. See [liveness](liveness.md).
- **Answer the questions only you can answer.** Each comes with a
  recommendation.
- **Send the drafts** you are happy with. Nothing goes out otherwise.

Check `wk status` and `wk lint` whenever you like. They are read-only.

## When something feels off

- A lane won't enter: run `wk status`, then `wk read --as <LANE> --headings`.
  Its latest coordinator post may not be its `ENTRY OPEN` any more.
- The coordinator seems asleep: check that exactly one reader is running, then
  send the watcher tick by hand.
- `wk lint` fails: it says which line and why. Never edit old posts to fix
  them. Post again.

Questions and reports are welcome as
[GitHub issues](https://github.com/CompuTish/watchkeeper/issues).
