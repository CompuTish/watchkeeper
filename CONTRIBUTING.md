# Contributing

Thank you for looking. Watchkeeper is young and deliberately small, so the
most useful contributions right now are reports from real use.

## Reports

Open an issue and say:

- which agent tool you used, and in which role (coordinator or lane);
- what you expected and what happened;
- the relevant part of your log, with anything private removed.

Reports that move a tool from "untested" to "works" (or "doesn't") in
[docs/tools.md](docs/tools.md) are especially welcome.

## Changes

- Keep the command free of dependencies beyond the Python 3.10 standard
  library, and keep `bin/watch.sh` to plain POSIX shell and awk.
- Every new rule should come from a real failure. Say what went wrong.
- Every new test should fail when the behaviour it guards is broken. Before
  opening a pull request, break the code on purpose, watch the test fail, then
  restore it.
- Rule text names roles, never particular models or vendors. Vendor names
  belong only in [docs/tools.md](docs/tools.md) and in examples.
- Write in plain British English, and explain terms on first use.

Run the tests with:

```sh
python3 -m unittest discover -s tests -t tests
```
