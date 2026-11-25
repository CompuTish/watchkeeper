# Security

## Reporting a vulnerability

Please report security problems privately, through GitHub's private
vulnerability reporting on this repository (the "Report a vulnerability"
button under the Security tab). Please don't open a public issue.

## What Watchkeeper does and doesn't do

- It reads and writes files in the workspace directory you give it. It makes no
  network connections and runs no commands from the log.
- `wk post` refuses posts containing strings shaped like secrets, and `wk lint`
  reports any found in the log without printing them. This is a safety net,
  not a guarantee. Don't rely on it to catch every secret.
- The log, status files, and cursors are plain text, readable by anyone with
  access to the directory. Don't keep them anywhere less private than the work
  they describe.
- The agents you connect are as powerful as the tools you give them.
  Watchkeeper's rules tell them to draft rather than send, and to stay inside
  the pipeline, but the real controls are the permissions you grant.
