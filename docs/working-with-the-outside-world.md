# Working with the outside world

A coordinator that only watches the lanes misses half the picture. Customers
write in, colleagues ask questions in chat, and the answer to a lane's question
is often sitting in someone's inbox. This page covers how the coordinator deals
with all of that safely.

The short version: **it reads widely, drafts freely, and sends nothing.**

## Where the access comes from

Watchkeeper has no connections of its own to chat, email, documents, or
anything else. The coordinator reaches them through whatever your agent tool
provides: built-in integrations, connectors, or command-line tools you have
already signed in to. Watchkeeper supplies the rules for using that access
safely, which is the rest of this page.

In one setup in daily use, the coordinator can read the code, the team's chat,
the owner's email, the shared documents, and the sprint board. When a customer
query, a support ticket, or a colleague's question arrives, a draft reply is
usually waiting before the owner has opened the message.

Give the coordinator read access first, and only what it needs. Anything that
writes, such as sending a message or changing a record, stays with the owner
(see [decision rights](decision-rights.md)).

## Sweeps

On each watcher tick, the coordinator sweeps the channels the owner has named:
specific chat channels, direct messages, and the owner's inbox and sent mail
for named correspondents. For each sweep:

- **Compute the lower bound from the clock.** "Messages since 14:05", where
  14:05 came from `date -u`, not from memory. A sweep that used a time in the
  future once missed a colleague's message.
- **Read the sent folder too.** Before telling the owner "you still need to
  reply to X", check that they haven't already.
- **Record what you saw** in the owner's notes: who, what, and what you
  drafted. One line each.

## Drafts, never sends

The coordinator may write a draft reply in the owner's mail or chat client,
ready for them to review and send. It never sends, posts, or replies on anyone's
behalf, however routine the message looks. This is the single most important
safety property of the whole design. The owner stays in charge of everything
that leaves the building.

Good drafts:

- **Reply in the thread of the person's own latest message**, not in an older
  thread of your own. People read the thread they last wrote in.
- **Reply to everyone on that message**, unless there is a reason not to.
- **Use plain language**, and check every factual claim against the live
  system before writing it down.
- **Name the source.** Each draft says which thread, document, or commit it
  relies on, so the owner can check it in seconds rather than take it on
  trust.
- **Respect the owner's tone.** If they have said "leave them to it", drop the
  follow-up questions.

## Never guess an address

Use an address that has been confirmed: from the person's own message, the
customer record, or the owner. Never construct one from a name and a domain.
A plausible guess is how a message reaches the wrong person.

## One source of truth per customer

If you track customers or accounts, pick one place per customer (a card, a
thread, or a record) and update it at once, tagging the person responsible. A
fact that lives in three places will be wrong in two of them.

## Changes to customer accounts

If the coordinator is permitted to change anything in a customer's account
(see [decision rights](decision-rights.md); the example policy doesn't permit
it), it works surgically:

1. Read the current state.
2. Change one thing, through the product's own supported route.
3. Read back and confirm the change.
4. Stop if the evidence contradicts the plan, and ask.

Next: [lessons](lessons.md).
