"""T6, T7, T25, T26, and T27: delivery, cursors, duplicates, and torn posts."""

import unittest

from helpers import END, WorkspaceTest

from watchkeeper.log import Workspace


class T06AllPostsInOneWindow(WorkspaceTest):
    def test_three_posts_in_one_window_are_all_delivered(self):
        self.post("ALPHA", "REQUEST", "OP-0001", to="COORDINATOR", body="first body")
        self.post("BETA", "REQUEST", "OP-0002", to="COORDINATOR", body="second body")
        self.post("ALPHA", "QUESTION", "about OP-0001", to="COORDINATOR", body="third body")
        code, out, _ = self.wk("watch", "--as", "COORDINATOR", "--timeout", "5", "--interval", "0.1")
        self.assertEqual(code, 0)
        for body in ("first body", "second body", "third body"):
            self.assertIn(body, out)
        self.assertIn("3 post(s)", out)

    def test_watch_times_out_and_names_silent_lanes(self):
        self.post("COORDINATOR", "NOTE", "starting", to="ALL LANES")
        code, out, _ = self.wk("watch", "--as", "COORDINATOR", "--timeout", "0", "--interval", "0.1")
        self.assertEqual(code, 2)
        self.assertIn("SILENT ALPHA never posted", out)
        self.assertIn("SILENT BETA never posted", out)

    def test_own_posts_do_not_wake_the_watcher(self):
        self.post("COORDINATOR", "NOTE", "only my own post", to="ALL LANES")
        code, out, _ = self.wk("watch", "--as", "COORDINATOR", "--timeout", "0", "--interval", "0.1")
        self.assertEqual(code, 2)
        self.assertNotIn("only my own post", out)


class T07AndT27CursorAdvancesOnlyOnAcknowledgement(WorkspaceTest):
    def read(self):
        return self.wk("read", "--as", "COORDINATOR")[1]

    def test_positive_control_acknowledged_posts_are_not_shown_again(self):
        self.post("ALPHA", "REQUEST", "OP-0001", to="COORDINATOR", body="alpha asks")
        self.assertIn("alpha asks", self.read())
        self.wk("read", "--as", "COORDINATOR", "--ack")
        self.assertIn("nothing new", self.read())

    def test_reading_without_acknowledging_redelivers_after_a_restart(self):
        self.post("ALPHA", "REQUEST", "OP-0001", to="COORDINATOR", body="alpha asks")
        self.assertIn("alpha asks", self.read())
        # The reader "dies" here. A successor starts with no memory, only the files.
        self.ws = Workspace(self.dir)
        out = self.read()
        self.assertIn("alpha asks", out)
        self.assertIn("REDELIVERED", out)

    def test_posts_arriving_between_read_and_ack_are_not_skipped(self):
        self.post("ALPHA", "REQUEST", "OP-0001", to="COORDINATOR", body="first")
        self.read()
        self.post("BETA", "REQUEST", "OP-0002", to="COORDINATOR", body="arrived late")
        self.wk("read", "--as", "COORDINATOR", "--ack")
        out = self.read()
        self.assertIn("arrived late", out)
        self.assertNotIn("first", out)

    def test_posting_never_moves_the_cursor(self):
        self.post("ALPHA", "REQUEST", "OP-0001", to="COORDINATOR", body="lane question")
        self.post("COORDINATOR", "NOTE", "my own note", to="BETA")
        self.assertIn("lane question", self.read())


class T25DuplicateDelivery(WorkspaceTest):
    def test_redelivered_post_appears_once_and_is_marked(self):
        self.post("ALPHA", "REQUEST", "OP-0001", to="COORDINATOR", body="unique-body-text")
        first = self.wk("read", "--as", "COORDINATOR")[1]
        second = self.wk("read", "--as", "COORDINATOR")[1]
        self.assertEqual(first.count("unique-body-text"), 1)
        self.assertNotIn("REDELIVERED", first)
        self.assertEqual(second.count("unique-body-text"), 1)
        self.assertEqual(second.count("REDELIVERED"), 1)

    def test_retrying_a_post_does_not_write_it_twice(self):
        self.post("COORDINATOR", "GO", "OP-0001", "deploy once", to="ALPHA", body="go")
        out = self.post("COORDINATOR", "GO", "OP-0001", "deploy once", to="ALPHA", body="go")
        self.assertIn("already posted", out)
        self.assertEqual(self.log_text().count("GO — OP-0001 — deploy once"), 1)


class T26TornAppend(WorkspaceTest):
    TORN = "## ALPHA → COORDINATOR: RELEASED — OP-0001 — 2020-01-01T00:00:00Z\nresidue zero, evid"

    def test_unfinished_last_post_is_not_delivered(self):
        self.append_raw(self.TORN)
        code, out, _ = self.wk("watch", "--as", "COORDINATOR", "--timeout", "0", "--interval", "0.1")
        self.assertEqual(code, 2)
        self.assertNotIn("residue", out)

    def test_torn_post_followed_by_another_is_flagged(self):
        self.append_raw(self.TORN)
        self.post("BETA", "REQUEST", "OP-0002", to="COORDINATOR", body="beta asks")
        out = self.wk("read", "--as", "COORDINATOR")[1]
        self.assertIn("TORN", out)
        self.assertIn("residue zero", out)
        self.assertIn("beta asks", out)
        code, lint_out, _ = self.wk("lint")
        self.assertEqual(code, 1)
        self.assertIn("torn post", lint_out)

    def test_author_recovers_by_reposting_and_is_not_deduplicated_against_the_torn_copy(self):
        self.append_raw(self.TORN)
        self.post("ALPHA", "RELEASED", "OP-0001", to="COORDINATOR", body="residue zero, evidence in the card")
        posts = self.ws.posts()
        self.assertEqual(len(posts), 2)
        self.assertTrue(posts[0].torn)
        self.assertTrue(posts[1].complete)

    def test_positive_control_complete_log_lints_clean(self):
        self.post("ALPHA", "REQUEST", "OP-0001", to="COORDINATOR", body="fine")
        code, out, _ = self.wk("lint")
        self.assertEqual(code, 0, out)
        self.assertIn("clean: 1 post(s)", out)


if __name__ == "__main__":
    unittest.main()
