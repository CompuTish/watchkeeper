"""The shared log: one Markdown file with a rules head and an append-only foot.

A post looks like this::

    ## ALPHA → COORDINATOR: REQUEST — OP-0001 — 2030-01-07T18:00:05Z
    Head 1111111. Staging deploy plus one test order. About 25 minutes.
    <!-- /post -->

The heading is machine-readable, the body is free text for people, and the
closing comment proves the post was written completely.
"""

from __future__ import annotations

import fcntl
import os
import re
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

SEP = " — "  # space, em dash, space: separates heading fields
ARROW = " → "  # space, rightwards arrow, space: author → addressee
END = "<!-- /post -->"
FOOT_MARKER = "<!-- watchkeeper: posts below this line are append-only -->"

LOG_NAME = "LOG.md"
STATE_DIR = ".watchkeeper"
LANES_FILE = "lanes"
LOCK_FILE = "lock"

TS_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
NAME_RE = re.compile(r"^[A-Z][A-Z0-9-]*$")
HEADING_RE = re.compile(
    r"^## (?P<author>[A-Z][A-Z0-9-]*)"
    r"(?: → (?P<to>[A-Z][A-Z0-9-]*(?: LANES)?))?"
    r": (?P<rest>.+)$"
)

# Who may post each type. "LANE" means any lane name.
VOCABULARY = {
    "REQUEST": {"LANE"},
    "ENTERED": {"LANE"},
    "RELEASED": {"LANE"},
    "QUESTION": {"LANE", "COORDINATOR"},
    "HOLD": {"LANE", "COORDINATOR"},
    "ADMITTED": {"COORDINATOR"},
    "ENTRY OPEN": {"COORDINATOR"},
    "WITHDRAWN": {"COORDINATOR"},
    "GO": {"COORDINATOR"},
    "WAIT": {"COORDINATOR"},
    "ACCEPTED+RELEASED": {"COORDINATOR"},
    "RULING": {"COORDINATOR", "OWNER"},
    "NOTE": {"COORDINATOR", "OWNER"},
}

# Deliberate decisions about a lane's case. Anything else sent to an admitted
# lane (a NOTE, QUESTION, or RULING meant as housekeeping) would silently
# become its binding post, so `wk post` refuses it.
ADMISSION_TYPES = {"ADMITTED", "ENTRY OPEN", "WITHDRAWN", "ACCEPTED+RELEASED", "HOLD", "GO", "WAIT"}
# Types that close an admission.
CLOSING_TYPES = {"WITHDRAWN", "ACCEPTED+RELEASED"}

WINDOW_RE = re.compile(r"^\d{2}:\d{2}Z-\d{2}:\d{2}Z$")
OP_RE = re.compile(r"^[A-Z][A-Z0-9-]*$")


class WatchkeeperError(Exception):
    """A refusal the user should see, with no traceback."""


def now_utc() -> str:
    """The clock, never a typed time."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_ts(ts: str) -> datetime:
    return datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


@dataclass
class Post:
    heading: str
    body: list[str] = field(default_factory=list)
    start_line: int = 0  # 1-based line number of the heading
    end_line: int = 0  # 1-based line number of the END marker, 0 if missing
    torn: bool = False  # another heading began before this post ended

    @property
    def complete(self) -> bool:
        return self.end_line > 0

    @property
    def fields(self) -> dict | None:
        return parse_heading(self.heading)

    @property
    def author(self) -> str | None:
        f = self.fields
        return f["author"] if f else None

    def text(self) -> str:
        lines = [self.heading, *self.body]
        if self.complete:
            lines.append(END)
        return "\n".join(lines)


def parse_heading(line: str) -> dict | None:
    """Split a heading into author, addressee, type, details, and timestamp.

    Returns None if the line is not shaped like a post heading at all.
    """
    m = HEADING_RE.match(line)
    if not m:
        return None
    parts = m.group("rest").split(SEP)
    return {
        "author": m.group("author"),
        "to": m.group("to"),
        "type": parts[0],
        "details": parts[1:-1] if len(parts) > 1 else [],
        "ts": parts[-1] if len(parts) > 1 else "",
    }


def format_heading(author: str, to: str | None, kind: str, details: list[str], ts: str) -> str:
    who = author + (ARROW + to if to else "")
    return "## " + who + ": " + SEP.join([kind, *details, ts])


def read_lines(path: Path) -> list[str]:
    if not path.exists():
        raise WatchkeeperError(f"no log at {path}; run 'wk init' first")
    return path.read_text(encoding="utf-8").split("\n")


def foot_start(lines: list[str]) -> int:
    """Index of the first line after the foot marker (0-based)."""
    for i, line in enumerate(lines):
        if line.strip() == FOOT_MARKER:
            return i + 1
    raise WatchkeeperError(f"log has no foot marker line: {FOOT_MARKER}")


def parse_posts(lines: list[str], after_line: int = 0) -> list[Post]:
    """Parse posts in the foot whose heading is after 1-based line `after_line`."""
    start = max(foot_start(lines), after_line)
    posts: list[Post] = []
    current: Post | None = None
    for i in range(start, len(lines)):
        line = lines[i]
        if line.startswith("## "):
            if current is not None:
                current.torn = True
                posts.append(current)
            current = Post(heading=line, start_line=i + 1)
        elif current is not None:
            if line.strip() == END:
                current.end_line = i + 1
                posts.append(current)
                current = None
            else:
                current.body.append(line)
    if current is not None:
        posts.append(current)  # incomplete: still being written, or torn at EOF
    return posts


class Workspace:
    """A directory holding LOG.md, status/, and .watchkeeper/."""

    def __init__(self, root: str | os.PathLike | None = None):
        self.root = Path(root or os.environ.get("WATCHKEEPER_DIR") or ".").resolve()
        self.log = self.root / LOG_NAME
        self.status_dir = self.root / "status"
        self.state = self.root / STATE_DIR
        self.cursor_dir = self.state / "cursors"

    def lanes(self) -> list[str]:
        p = self.state / LANES_FILE
        if not p.exists():
            raise WatchkeeperError(f"no lanes file at {p}; run 'wk init' first")
        return [x.strip() for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]

    @contextmanager
    def locked(self):
        """Hold the workspace lock. Read state only after entering this block."""
        self.state.mkdir(parents=True, exist_ok=True)
        fd = os.open(self.state / LOCK_FILE, os.O_RDWR | os.O_CREAT, 0o644)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX)
            yield
        finally:
            fcntl.flock(fd, fcntl.LOCK_UN)
            os.close(fd)

    def lines(self) -> list[str]:
        return read_lines(self.log)

    def posts(self, after_line: int = 0) -> list[Post]:
        return parse_posts(self.lines(), after_line)

    def append(self, text: str) -> None:
        """Append in one write, so a reader sees all of a post or a torn one."""
        data = text.encode("utf-8")
        fd = os.open(self.log, os.O_WRONLY | os.O_APPEND)
        try:
            written = os.write(fd, data)
            if written != len(data):
                raise WatchkeeperError("short write to the log; run 'wk lint' before retrying")
            os.fsync(fd)
        finally:
            os.close(fd)
