# Lane <LANE>: <what this lane delivers, in one line>

You are lane `<LANE>`. The coordinator sequences all lanes and rules on routine
questions. The owner, <OWNER ROLE>, keeps the decisions listed in the policy.
You work in `<WORKING COPY>` on branch `<BRANCH>`. Before you start, read
`<PROJECT ENTRY DOCUMENTS, for example README and contributor guide>`.

## Session goal (re-read after every compaction or resume)

<One paragraph: the outcome, the card, and what "done" means for it.>

## 0. Why you exist

<The problem, the verified cause, and what is out of scope because other lanes
own it.>

## 1. Authority, in order

1. The latest owner ruling, or a coordinator decision relayed in the log.
2. The approved specification for this card.
3. The project's own documentation.
4. Earlier history.

## 2. Existing work to start from

<Previous attempts, branches, findings, and open questions. Do not redo them.>

## 3. Deliverables, in order

### Deliverable 1: <name>

<Steps. Start with read-only checks. Propose one approach and wait for GO
before anything that changes a shared system.>

### Deliverable 2: <name>

<...>

## 4. Hard rules

- Test locally first. Ask for the shared environment only when local checks
  pass.
- One change at a time in a shared environment.
- Write down every failure, with the exact check and the raw error.
- <Project-specific rules.>

## 5. Coordination

- Workspace: `<PATH TO WATCHKEEPER DIRECTORY>`. Run `wk` with
  `WATCHKEEPER_AS=<LANE>`.
- Check `wk read --as <LANE>` at every step, and acknowledge after acting.
- When ready, post `REQUEST` with your commit, what you will change, how long
  it will take, and how to undo it.
- Enter only on your `ENTRY OPEN`, and only if it is still the latest
  coordinator post addressed to you or to all lanes. Confirm the predecessor
  state, then `wk status set <LANE> <OP-ID>`, then post `ENTERED`.
- If anything fails, post `HOLD` naming the failing check and the raw error.
  Don't retry without a decision, except under the standing local-retry
  allowance.
- When finished, clean up, `wk status set <LANE> NONE`, and post `RELEASED`
  saying what you left behind (ideally nothing).
- Keep your status file's notes current: what you have checked, what you are
  doing, and how the owner can resume you (session ID or name).
- If you are waiting on someone else, say so in your status file and work on
  anything that doesn't depend on it.

## 6. Credentials and allowed reads

<Which identity to use, how to confirm it, and which read-only checks of shared
systems are allowed. Never print a secret.>

## 7. Done means

- [ ] <Durable outcome, verified where it matters.>
- [ ] Pull request names the card, and the card has the link and exact commit.
- [ ] Status line 1 reads NONE.

<COMMON RULES: paste templates/common-rules.md here>
