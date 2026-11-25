# Handover: <from> to <to>, <UTC time from the clock>

Write this before a coordinator session ends, before the owner goes offline,
or before a lane hands its work to another. A fresh session should be able to
continue from this file and the workspace alone.

## Where things stand

- Environment: <FREE, or held by LANE for OP-ID since ...>.
- Lanes: one line each, with card, state, and how to resume it.
- Open admissions and their windows: <...>.
- Last acknowledged log line: <n>.

## Standing instructions

- Owner rulings in force, word for word, with what each replaced: <...>.
- Mandates in force, with their bounds and expiry: <...>.

## Next steps, in order

1. <...>
2. <...>

## Decisions waiting for the owner

- <Question, options, recommendation.>

## Things to check first

- Exactly one blocking reader running.
- Free disk space.
- Credentials and sign-ins needed overnight, with expiry times from the tool
  that issued them, not estimated.

## Before going offline (owner)

- Record any new mandate in full, with its bounds.
- Settle any decision that would otherwise stall a lane overnight.
- Set the order of work and the deadlines.
- Update the watcher tick prompt if anything has changed.
