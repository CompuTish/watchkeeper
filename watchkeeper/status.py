"""Lane status files. Line 1 is the reservation; everything below is the lane's notes.

    # CURRENT RESERVATION: OP-0001 — 2030-01-07T18:05:02Z

Only the lane that owns a status file writes it. Anyone may read it. A line 1
that cannot be read counts as busy, because guessing "free" is the expensive
mistake.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass

from .log import CLOSING_TYPES, SEP, Workspace, WatchkeeperError, now_utc

LINE_RE = re.compile(r"^# CURRENT RESERVATION: (?P<op>NONE|[A-Z][A-Z0-9-]*) — (?P<ts>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z)$")


@dataclass
class Status:
    lane: str
    op: str | None  # None means unknown
    ts: str | None
    error: str | None = None

    @property
    def busy(self) -> bool:
        return self.op != "NONE"


def status_path(ws: Workspace, lane: str):
    return ws.status_dir / f"{lane}.md"


def format_line(op: str, ts: str) -> str:
    return f"# CURRENT RESERVATION: {op}{SEP}{ts}"


def read_status(ws: Workspace, lane: str) -> Status:
    p = status_path(ws, lane)
    if not p.exists():
        return Status(lane, None, None, "missing status file (counts as busy)")
    first = p.read_text(encoding="utf-8").split("\n", 1)[0]
    m = LINE_RE.match(first)
    if not m:
        return Status(lane, None, None, "line 1 is malformed (counts as busy)")
    return Status(lane, m.group("op"), m.group("ts"))


def write_status(ws: Workspace, lane: str, op: str) -> str:
    """Replace line 1, keeping the lane's notes below it."""
    p = status_path(ws, lane)
    rest = ""
    if p.exists():
        parts = p.read_text(encoding="utf-8").split("\n", 1)
        rest = parts[1] if len(parts) > 1 else ""
    line = format_line(op, now_utc())
    tmp = p.with_suffix(".md.tmp")
    tmp.write_text(line + "\n" + rest, encoding="utf-8")
    os.replace(tmp, p)
    return line


def binding_post(ws: Workspace, lane: str):
    """The latest coordinator post addressed to this lane or to ALL LANES.

    During an admission, this post is the lane's authority. Anything else sent
    to the lane in between replaces it.
    """
    for p in reversed(ws.posts()):
        f = p.fields
        if p.complete and f and f["author"] == "COORDINATOR" and f["to"] in (lane, "ALL LANES"):
            return p
    return None


def open_admissions(ws: Workspace) -> dict[str, str]:
    """Lanes with an ADMITTED or ENTRY OPEN that has not been closed: lane -> op."""
    active: dict[str, str] = {}
    for p in ws.posts():
        f = p.fields
        if not (p.complete and f and f["details"]):
            continue
        op = f["details"][0]
        if f["author"] == "COORDINATOR" and f["type"] in ("ADMITTED", "ENTRY OPEN") and f["to"]:
            active[f["to"]] = op
        elif f["type"] in CLOSING_TYPES and f["to"] in active and active[f["to"]] == op:
            del active[f["to"]]
    return active


def reserve(ws: Workspace, lane: str, op: str) -> str:
    """Take the environment for `op`, or release it with op == 'NONE'.

    Taking it needs two things, both read after the lock is held:
    the lane's binding post is ENTRY OPEN for this exact operation, and every
    other lane's line 1 reads NONE.
    """
    lanes = ws.lanes()
    if lane not in lanes:
        raise WatchkeeperError(f"unknown lane {lane!r}")
    with ws.locked():
        if op == "NONE":
            return write_status(ws, lane, "NONE")
        p = binding_post(ws, lane)
        f = p.fields if p else None
        if not f or f["type"] != "ENTRY OPEN" or f["to"] != lane or not f["details"] or f["details"][0] != op:
            shown = p.heading if p else "nothing"
            raise WatchkeeperError(
                f"refused: {lane}'s latest coordinator post must be 'ENTRY OPEN — {op} — <window>', "
                f"but it is: {shown}"
            )
        busy = [s for s in (read_status(ws, x) for x in lanes if x != lane) if s.busy]
        if busy:
            who = ", ".join(f"{s.lane} ({s.op or s.error})" for s in busy)
            raise WatchkeeperError(f"refused: the environment is busy: {who}")
        return write_status(ws, lane, op)
