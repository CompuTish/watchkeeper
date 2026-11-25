# Changelog

## 0.1.0 (25 November 2026)

First public release: the protocol and a starter kit.

- Protocol documentation, in teaching order, and a catalogue of lessons from
  real use.
- Templates: coordinator and lane prompts, common rules, the watcher tick, an
  owner update, a handover, a review prompt, an example decision-rights
  policy, and the log head.
- `wk`, a small command with no dependencies beyond Python 3.10: `init`,
  `post`, `read`, `watch`, `lint`, and `status`.
- `bin/watch.sh`, a blocking reader in plain POSIX shell.
- A toy two-lane example that replays in about a second, and a guide to
  setting it up on your own project.
- Guidance on how the coordinator reaches chat, email, and documents through
  your agent tool, and a rule that every draft names its source.
- Tests for the lock, status lines, vocabulary, clock timestamps, secrets,
  delivery, cursors, duplicates, and torn posts, run on Linux and macOS.
