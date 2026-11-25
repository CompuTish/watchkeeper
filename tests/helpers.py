"""Shared helpers: a throwaway workspace and a way to run the command in-process."""

from __future__ import annotations

import io
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from watchkeeper.cli import main  # noqa: E402
from watchkeeper.log import END, FOOT_MARKER, Workspace  # noqa: E402


class WorkspaceTest(unittest.TestCase):
    lanes = "ALPHA,BETA"

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)
        self.ws = Workspace(self.dir)
        code, out, err = self.wk("init", "--lanes", self.lanes)
        self.assertEqual(code, 0, err)

    def tearDown(self):
        self._tmp.cleanup()

    def wk(self, *args: str) -> tuple[int, str, str]:
        """Run `wk <args> --dir <workspace>` in-process."""
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = main([args[0], "--dir", str(self.dir), *args[1:]])
        return code, out.getvalue(), err.getvalue()

    def wk_process(self, *args: str, **kw) -> subprocess.Popen:
        """Run `wk` as a separate process, for tests that need real concurrency."""
        env = dict(os.environ, PYTHONPATH=str(REPO))
        return subprocess.Popen(
            [sys.executable, "-m", "watchkeeper", args[0], "--dir", str(self.dir), *args[1:]],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env, **kw,
        )

    def post(self, author: str, kind: str, *details: str, to: str | None = None, body: str = "") -> str:
        args = ["post", "--as", author, kind, *details]
        if to:
            args += ["--to", to]
        if body:
            args += ["--body", body]
        code, out, err = self.wk(*args)
        self.assertEqual(code, 0, f"post refused: {err}")
        return out

    def append_raw(self, text: str) -> None:
        """Write to the log by hand, as an agent without the tool would."""
        with open(self.ws.log, "a", encoding="utf-8") as f:
            f.write(text)

    def log_text(self) -> str:
        return self.ws.log.read_text(encoding="utf-8")


__all__ = ["END", "FOOT_MARKER", "REPO", "WorkspaceTest"]
