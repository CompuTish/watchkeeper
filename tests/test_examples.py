"""The toy example replays end to end, the shell reader agrees with the tool,
and the log head shipped in the package matches the template."""

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from helpers import REPO, WorkspaceTest


class ToyExampleReplays(unittest.TestCase):
    def test_replay_runs_to_a_clean_final_state(self):
        with tempfile.TemporaryDirectory() as d:
            env = dict(os.environ, WK=f"{REPO / 'bin' / 'wk'}")
            run = subprocess.run(["sh", str(REPO / "examples/toy-project/replay.sh"), d],
                                 capture_output=True, text=True, env=env, timeout=120)
            self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
            log = Path(d, "LOG.md").read_text()
            headings = [l for l in log.split("\n") if l.startswith("## ") and " — " in l]
            self.assertGreaterEqual(len(headings), 15)  # the replay actually posted
            for expected in ["REQUEST — OP-0001", "ENTRY OPEN — OP-0001", "HOLD — OP-0001",
                             "ACCEPTED+RELEASED — OP-0001", "ACCEPTED+RELEASED — OP-0002"]:
                self.assertIn(expected, log)
            self.assertNotIn("NOTE — disk check", log)  # the refused note never landed
            self.assertEqual(run.stdout.count("(refused as expected)"), 2)
            self.assertIn("environment: FREE", run.stdout)
            self.assertIn("clean:", run.stdout)


@unittest.skipUnless(shutil.which("sh") and shutil.which("awk"), "needs a POSIX shell and awk")
class ShellReaderAgrees(WorkspaceTest):
    def sh(self, *args):
        return subprocess.run(["sh", str(REPO / "bin/watch.sh"), "-d", str(self.dir), *args],
                              capture_output=True, text=True, timeout=30)

    def test_shell_reader_delivers_redelivers_and_acknowledges(self):
        self.post("ALPHA", "REQUEST", "OP-0001", to="COORDINATOR", body="alpha asks")
        self.post("BETA", "REQUEST", "OP-0002", to="COORDINATOR", body="beta asks")
        self.post("COORDINATOR", "NOTE", "my own", to="ALL LANES")
        first = self.sh("-t", "0", "COORDINATOR")
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertIn("alpha asks", first.stdout)
        self.assertIn("beta asks", first.stdout)
        self.assertNotIn("my own", first.stdout)
        again = self.sh("-t", "0", "COORDINATOR")
        self.assertEqual(again.stdout.count("REDELIVERED"), 2)
        self.assertEqual(self.sh("-a", "COORDINATOR").returncode, 0)
        # The Python tool reads the same cursor file and agrees nothing is new.
        self.assertIn("nothing new", self.wk("read", "--as", "COORDINATOR")[1])
        quiet = self.sh("-t", "0", "-s", "0", "COORDINATOR")
        self.assertEqual(quiet.returncode, 2)
        self.assertIn("SILENT ALPHA since", quiet.stdout)

    def test_shell_reader_flags_torn_posts(self):
        self.append_raw("## ALPHA → COORDINATOR: RELEASED — OP-0001 — 2020-01-01T00:00:00Z\ncut sh")
        self.post("BETA", "REQUEST", "OP-0002", to="COORDINATOR", body="beta asks")
        out = self.sh("-t", "0", "COORDINATOR").stdout
        self.assertIn("TORN", out)
        self.assertIn("beta asks", out)


class LogHeadTemplateMatchesPackage(unittest.TestCase):
    def test_template_is_the_shipped_head(self):
        self.assertEqual((REPO / "templates/log-head.md").read_text(),
                         (REPO / "watchkeeper/log_head.md").read_text())


class CommandRunsAsAModule(unittest.TestCase):
    def test_version(self):
        run = subprocess.run([sys.executable, "-m", "watchkeeper", "--version"], capture_output=True, text=True,
                             env=dict(os.environ, PYTHONPATH=str(REPO)), timeout=30)
        self.assertEqual(run.returncode, 0)
        self.assertIn("watchkeeper 0.1.0", run.stdout)


if __name__ == "__main__":
    unittest.main()
