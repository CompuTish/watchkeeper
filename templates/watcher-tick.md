# Watcher tick

Send this prompt to the coordinator on a schedule: every 15 minutes while lanes
are busy, hourly when things are quiet. It is the same every time. Edit the
bracketed parts once, when you set it up.

```text
Watcher tick. Do these in order, then return to your loop.

1. Read the log from your cursor: wk read --as COORDINATOR. Deal with every
   post, then acknowledge.
2. Sweep for anything new since your last sweep, using a lower bound computed
   from `date -u`: chat channels <CHANNELS>, direct messages, and the owner's
   inbox and sent mail for <PEOPLE OR CUSTOMERS>.
3. For anything that needs a reply, write a draft in the thread of the
   person's own latest message, and name the thread, document, or commit it
   relies on. Do not send anything.
4. Record each change of state in the owner's notes: one line each, with the
   time from the clock.
5. Make sure exactly one blocking reader is running. Start one if none is,
   and stop any extras.
6. Check free disk space, and whether the environment is idle while a lane
   waits. If a lane needs resuming, put it at the top of the owner update.
7. Never print a secret.
8. If nothing has changed, do nothing visible and say nothing.
```
