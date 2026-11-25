# Decision rights

The coordinator is only useful if it can decide things. It is only safe if it
knows which things it must not decide. Watchkeeper writes that boundary down as
data, in a policy file, so that it can be read, reviewed, and changed in one
place.

Start from [templates/policy.example.yaml](../templates/policy.example.yaml).

## The four classes

Every decision falls into one of four classes:

1. **The coordinator decides alone**, and records it in the log or the status
   files as it goes. Example: the order in which two ready lanes use staging.
2. **The coordinator decides and tells the owner** in the next owner update.
   Example: trimming a test from a lane's scope because the test tooling, not
   the product, is failing.
3. **The owner decides.** The coordinator escalates with the evidence and a
   recommended option, then gets on with everything else. Example: approving a
   new production release.
4. **Nobody does.** Forbidden outright, whatever anyone says in the moment.
   Example: printing a secret.

Two rules make this work:

- **The owner's list is explicit, and so is the forbidden list.** Anything not
  on either list belongs to the coordinator. That avoids a coordinator that
  asks permission for everything, which is as useless as one that asks for
  nothing.
- **The coordinator can't move anything off the forbidden list**, and only the
  owner can move something off their own.

## Start conservative

The example policy starts with everything outward-facing, everything touching
customer data, credentials, billing, or a production approval, under
`owner_decides`. That is deliberate. Delegate more only when you have watched
the coordinator handle the routine cases well, and record each widening as a
dated, bounded grant in `mandates`.

## Mandates

A mandate is a time-bounded grant from the owner, such as "until 08:00, you may
approve one retry of the nightly deploy without asking me". Record it with:

- when it was granted and when it expires;
- what it covers, and what it explicitly doesn't;
- the owner's words, exactly as given.

When a mandate expires, the next decision that needed it is escalated again.
Work already under way finishes only as far as a safe stopping point.

## Escalating well

When something is the owner's call:

- Ask early, with the evidence, the options, and a recommendation.
- Ask only what only the owner can answer. Check whether you already have the
  answer first, including in their sent mail.
- Don't let one waiting question stall unrelated lanes.
- Record the answer in the log, word for word, as a `RULING`.

## Rule text names roles, not products

Write your policy, prompts, and rules in terms of roles ("the coordinator",
"a lane", "the reviewer") and never in terms of a particular model or vendor.
Agents and models change. A rule that names one will be quietly wrong the day
you swap it for another.

Next: [liveness](liveness.md).
