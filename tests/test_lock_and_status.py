"""The environment lock and status line 1."""

import time
import unittest

from helpers import WorkspaceTest


class LockRereadsStateAfterAcquiring(WorkspaceTest):
    """Whoever gets the lock second re-reads state and sees busy."""

    def open_entry(self, lane, op):
        self.post("COORDINATOR", "ENTRY OPEN", op, "18:00Z-18:30Z", to=lane)

    def test_positive_control_entry_succeeds_when_free(self):
        self.open_entry("ALPHA", "OP-0001")
        code, out, err = self.wk("status", "set", "ALPHA", "OP-0001")
        self.assertEqual(code, 0, err)
        self.assertTrue(self.ws.status_dir.joinpath("ALPHA.md").read_text().startswith("# CURRENT RESERVATION: OP-0001 — "))

    def test_state_is_read_after_the_lock_is_acquired(self):
        self.open_entry("ALPHA", "OP-0001")
        # Hold the lock, start ALPHA's attempt, and change the world while it waits.
        with self.ws.locked():
            proc = self.wk_process("status", "set", "ALPHA", "OP-0001")
            time.sleep(0.8)  # ALPHA is now blocked on the lock
            self.assertIsNone(proc.poll(), "the attempt should be waiting for the lock")
            beta = self.ws.status_dir / "BETA.md"
            beta.write_text("# CURRENT RESERVATION: OP-0002 — 2030-01-07T18:00:00Z\n")
        out, err = proc.communicate(timeout=20)
        self.assertEqual(proc.returncode, 1, out)
        self.assertIn("busy", err)
        self.assertIn("OP-0002", err)
        self.assertIn("NONE", self.ws.status_dir.joinpath("ALPHA.md").read_text().split("\n")[0])

    def test_two_simultaneous_attempts_exactly_one_wins(self):
        # A careless coordinator opens entry for both lanes at once.
        self.open_entry("ALPHA", "OP-0001")
        self.open_entry("BETA", "OP-0002")
        with self.ws.locked():
            a = self.wk_process("status", "set", "ALPHA", "OP-0001")
            b = self.wk_process("status", "set", "BETA", "OP-0002")
            time.sleep(0.8)
        a.communicate(timeout=20)
        b.communicate(timeout=20)
        codes = sorted([a.returncode, b.returncode])
        self.assertEqual(codes, [0, 1])


class MalformedStatusIsBusy(WorkspaceTest):
    """A status line that cannot be read counts as busy."""

    def setUp(self):
        super().setUp()
        self.post("COORDINATOR", "ENTRY OPEN", "OP-0001", "18:00Z-18:30Z", to="ALPHA")

    def test_positive_control_well_formed_none_is_free(self):
        code, _, err = self.wk("status", "set", "ALPHA", "OP-0001")
        self.assertEqual(code, 0, err)

    def test_malformed_line_blocks_entry(self):
        for bad in [
            "# CURRENT RESERVATION: none — 2030-01-07T18:00:00Z\n",  # lower case
            "# CURRENT RESERVATION: NONE\n",  # no timestamp
            "# CURRENT RESERVATION: NONE — 2030-01-07T18:00:00.123456+00:00\n",  # wrong time shape
            "CURRENT RESERVATION: NONE — 2030-01-07T18:00:00Z\n",  # not line-1 format
            "",  # empty file
        ]:
            with self.subTest(bad=bad):
                self.ws.status_dir.joinpath("BETA.md").write_text(bad)
                code, _, err = self.wk("status", "set", "ALPHA", "OP-0001")
                self.assertEqual(code, 1)
                self.assertIn("busy", err)

    def test_missing_file_blocks_entry(self):
        self.ws.status_dir.joinpath("BETA.md").unlink()
        code, _, err = self.wk("status", "set", "ALPHA", "OP-0001")
        self.assertEqual(code, 1)
        self.assertIn("busy", err)

    def test_status_shows_malformed_as_busy_and_never_rewrites_it(self):
        bad = "garbage\nBETA's notes\n"
        self.ws.status_dir.joinpath("BETA.md").write_text(bad)
        code, out, _ = self.wk("status")
        self.assertEqual(code, 0)
        self.assertRegex(out, r"BETA\s+BUSY")
        self.assertIn("environment: BUSY", out)
        self.assertEqual(self.ws.status_dir.joinpath("BETA.md").read_text(), bad)


class EntryNeedsTheExactTrigger(WorkspaceTest):
    """The clock never grants permission, and nor does a different post."""

    def test_no_entry_without_entry_open(self):
        self.post("COORDINATOR", "ADMITTED", "OP-0001", to="ALPHA")
        code, _, err = self.wk("status", "set", "ALPHA", "OP-0001")
        self.assertEqual(code, 1)
        self.assertIn("ENTRY OPEN", err)

    def test_entry_open_for_another_operation_does_not_count(self):
        self.post("COORDINATOR", "ENTRY OPEN", "OP-0009", "18:00Z-18:30Z", to="ALPHA")
        code, _, _ = self.wk("status", "set", "ALPHA", "OP-0001")
        self.assertEqual(code, 1)

    def test_a_later_post_replaces_the_entry_open(self):
        self.post("COORDINATOR", "ENTRY OPEN", "OP-0001", "18:00Z-18:30Z", to="ALPHA")
        self.post("COORDINATOR", "WAIT", "OP-0001", "staging is unhealthy", to="ALPHA")
        code, _, err = self.wk("status", "set", "ALPHA", "OP-0001")
        self.assertEqual(code, 1)
        self.assertIn("WAIT", err)

    def test_housekeeping_to_an_admitted_lane_is_refused(self):
        self.post("COORDINATOR", "ADMITTED", "OP-0001", to="ALPHA")
        code, _, err = self.wk("post", "--as", "COORDINATOR", "--to", "ALL LANES", "NOTE", "disk check")
        self.assertEqual(code, 1)
        self.assertIn("open admission", err)
        # Positive control: after the case closes, the same note is accepted.
        self.post("COORDINATOR", "WITHDRAWN", "OP-0001", to="ALPHA")
        self.post("COORDINATOR", "NOTE", "disk check", to="ALL LANES")


if __name__ == "__main__":
    unittest.main()
