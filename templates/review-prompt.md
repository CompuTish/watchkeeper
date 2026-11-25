# Review prompt

Use this to ask a separate reviewer agent, in a fresh session, to review one
pull request at one exact commit. Fresh matters: a resumed session can quietly
run with different settings, or remember things the code doesn't say.

```text
You are reviewing pull request <LINK> on branch <BRANCH>.
Head commit: <full 40-character hash>. Base: <full hash>.
The working copy you are in is checked out at that exact head. Confirm it
before you start, and stop if it isn't.

Read <PROJECT ENTRY DOCUMENTS> first.

Do not change any file. Do not run anything that writes to a shared system.
Your verdict goes to standard output, and the coordinator relays it.

Scope: <what this change is meant to do, and what it must not touch>.
Context: <the card, the problem, and the evidence so far>.

Evaluate, end to end:
1. Diagnosis: is the cause the real cause?
2. Completeness: does the change fix it everywhere it occurs?
3. Risks: what could this break, for whom, and how would we know?
4. Scope: does it change anything it shouldn't?

End with exactly one line, VERDICT: APPROVE or VERDICT: REQUEST_CHANGES,
followed by any blocking findings as file:line with a one-line reason each.
```

When relaying a verdict in the log, say which commit was reviewed, quote the
verdict line exactly, and say what the reviewer couldn't check.
