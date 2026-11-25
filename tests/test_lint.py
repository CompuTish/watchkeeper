"""T4, T5, and T19: vocabulary, clock timestamps, and secrets."""

import unittest

from helpers import END, WorkspaceTest

from watchkeeper.lint import check_heading, find_secrets, lint_posts
from watchkeeper.log import parse_posts, FOOT_MARKER

LANES = ["ALPHA", "BETA"]
GOOD = "## ALPHA → COORDINATOR: REQUEST — OP-0001 — 2030-01-07T18:00:05Z"


class T04Vocabulary(unittest.TestCase):
    def test_positive_control_good_headings_pass(self):
        for h in [
            GOOD,
            "## COORDINATOR → ALPHA: ENTRY OPEN — OP-0001 — 18:05Z-18:35Z — 2030-01-07T18:03:10Z",
            "## COORDINATOR → ALL LANES: NOTE — disk check — 2030-01-07T18:03:10Z",
            "## OWNER: RULING — no production deploys tonight — 2030-01-07T18:03:10Z",
        ]:
            with self.subTest(h=h):
                self.assertEqual(check_heading(h, LANES), [])

    def test_bad_headings_are_rejected(self):
        cases = {
            "## ALPHA → COORDINATOR: DONE — OP-0001 — 2030-01-07T18:00:05Z": "not in the vocabulary",
            "## COORDINATOR → ALPHA: WAIT — stop the deploy — 2030-01-07T18:00:05Z": "stop",
            "## COORDINATOR → ALPHA: OPEN ENTRY — OP-0001 — 18:05Z-18:35Z — 2030-01-07T18:00:05Z": "paraphrase",
            "## COORDINATOR → ALPHA: ENTRY-OPEN — OP-0001 — 18:05Z-18:35Z — 2030-01-07T18:00:05Z": "paraphrase",
            "## COORDINATOR → ALPHA: ENTRY OPEN — OP-0001 — 2030-01-07T18:00:05Z": "exactly",
            "## COORDINATOR → ALPHA: ENTRY OPEN — OP-0001 — after BETA — 2030-01-07T18:00:05Z": "exactly",
            "## COORDINATOR → ALPHA: GO — entry open now — 2030-01-07T18:00:05Z": "entry trigger",
            "## ALPHA → BETA: ENTRY OPEN — OP-0001 — 18:05Z-18:35Z — 2030-01-07T18:00:05Z": "may not be posted by ALPHA",
            "## GAMMA → COORDINATOR: REQUEST — OP-0001 — 2030-01-07T18:00:05Z": "unknown author",
            "## ALPHA → COORDINATOR: REQUEST — 2030-01-07T18:00:05Z": "name its operation",
            "## ALPHA: REQUEST OP-0001": "clock time",
            "ALPHA wants OP-0001": "not a post heading",
        }
        for heading, expected in cases.items():
            with self.subTest(heading=heading):
                errs = check_heading(heading, LANES)
                self.assertTrue(errs, "should have been rejected")
                self.assertIn(expected, " ".join(errs))


class T04PostRefusesBadVocabulary(WorkspaceTest):
    def test_post_refuses_and_writes_nothing(self):
        before = self.log_text()
        for args in [
            ("post", "--as", "ALPHA", "--to", "COORDINATOR", "DONE", "OP-0001"),
            ("post", "--as", "COORDINATOR", "--to", "ALPHA", "WAIT", "OP-0001", "stop everything"),
            ("post", "--as", "COORDINATOR", "--to", "ALPHA", "OPEN ENTRY", "OP-0001", "18:05Z-18:35Z"),
        ]:
            with self.subTest(args=args):
                code, _, err = self.wk(*args)
                self.assertEqual(code, 1)
                self.assertIn("refused", err)
        self.assertEqual(self.log_text(), before)
        # Positive control: a good post on the same workspace is accepted.
        self.post("ALPHA", "REQUEST", "OP-0001", to="COORDINATOR")
        self.assertIn("REQUEST — OP-0001", self.log_text())


def foot(*posts: str) -> list[str]:
    return ("# head\n" + FOOT_MARKER + "\n" + "".join(posts)).split("\n")


def p(heading: str, body: str = "body") -> str:
    return f"{heading}\n{body}\n{END}\n\n"


class T05TypedTimestamps(unittest.TestCase):
    NOW = "2030-01-07T19:00:00Z"

    def lint(self, *posts):
        return lint_posts(parse_posts(foot(*posts)), LANES, now=self.NOW)

    def test_positive_control_clock_times_in_order_pass(self):
        self.assertEqual(self.lint(
            p("## ALPHA → COORDINATOR: REQUEST — OP-0001 — 2030-01-07T18:00:05Z"),
            p("## COORDINATOR → ALPHA: ADMITTED — OP-0001 — 2030-01-07T18:03:10Z"),
        ), [])

    def test_future_time_is_rejected(self):
        errs = self.lint(p("## ALPHA → COORDINATOR: REQUEST — OP-0001 — 2030-01-07T19:13:00Z"))
        self.assertIn("future", " ".join(errs))

    def test_time_earlier_than_previous_post_is_rejected(self):
        errs = self.lint(
            p("## ALPHA → COORDINATOR: REQUEST — OP-0001 — 2030-01-07T18:30:00Z"),
            p("## COORDINATOR → ALPHA: ADMITTED — OP-0001 — 2030-01-07T18:10:00Z"),
        )
        self.assertIn("earlier than the post before it", " ".join(errs))

    def test_wrong_shape_or_missing_time_is_rejected(self):
        for ts in ["2030-01-07 18:00", "2030-01-07T18:00Z", "2030-01-07T18:00:00.123+00:00", "about six"]:
            with self.subTest(ts=ts):
                errs = self.lint(p(f"## ALPHA → COORDINATOR: REQUEST — OP-0001 — {ts}"))
                self.assertIn("clock time", " ".join(errs))


class T05PostStampsTheClock(WorkspaceTest):
    def test_post_writes_the_current_time(self):
        from datetime import datetime, timezone
        out = self.post("ALPHA", "REQUEST", "OP-0001", to="COORDINATOR")
        ts = out.strip().rsplit(" — ", 1)[1]
        stamped = datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        self.assertLess(abs((datetime.now(timezone.utc) - stamped).total_seconds()), 5)


# Fake values, assembled at runtime so that secret scanners don't flag this file.
SECRETS = {
    "private key": "-----BEGIN OPENSSH PRIVATE KEY-----",
    "cloud access key": "key " + "AKIA" + "ABCDEFGHIJKLMNOP" + " here",
    "source-host token": "ghp_abcdefghijklmnopqrstuvwxyz0123456789",
    "API key": "sk-abcdefghijklmnopqrstuvwxyz012345",
    "chat token": "xo" + "xb-1234567890-abcdefghij",
    "JSON web token": "ey" + "JhbGciOiJIUzI1NiJ9." + "ey" + "JzdWIiOiIxMjM0NTY3ODkwIn0.abcdefghijklmnop",
    "credentials in a URL": "postgres://app:s3cretpass@db.example.test:5432/app",
    "password or secret assignment": "password=correct-horse-battery",
}


class T19Secrets(WorkspaceTest):
    def test_positive_control_ordinary_text_is_not_a_secret(self):
        self.assertEqual(find_secrets("Head 1111111. Staging on revision 42. See https://example.test/docs."), [])

    def test_each_secret_shape_is_found(self):
        for kind, text in SECRETS.items():
            with self.subTest(kind=kind):
                self.assertIn(kind, [k for _, k in find_secrets(text)])

    def test_post_refuses_secrets_without_echoing_them(self):
        before = self.log_text()
        for kind, text in SECRETS.items():
            with self.subTest(kind=kind):
                code, out, err = self.wk("post", "--as", "ALPHA", "--to", "COORDINATOR", "HOLD", "OP-0001",
                                         "--body", f"the value is {text}")
                self.assertEqual(code, 1)
                self.assertIn(kind, err)
                self.assertNotIn(text, err + out)
        self.assertEqual(self.log_text(), before)

    def test_lint_finds_a_secret_written_by_hand(self):
        self.append_raw(p("## ALPHA → COORDINATOR: HOLD — OP-0001 — 2020-01-01T00:00:00Z",
                          "connect with postgres://app:s3cretpass@db.example.test/app"))
        code, out, _ = self.wk("lint")
        self.assertEqual(code, 1)
        self.assertIn("credentials in a URL", out)
        self.assertNotIn("s3cretpass", out)


if __name__ == "__main__":
    unittest.main()
