"""Read cursors: where each reader has got to in the log.

A cursor holds two line numbers:

- delivered: the last line shown to the reader;
- acknowledged: the last line the reader has said it has dealt with.

Reading never moves "acknowledged". Only an explicit acknowledgement does. So
a reader that crashes, restarts, or loses its context after seeing posts but
before acting on them gets them again, marked as redelivered.

The file is plain text, "<acknowledged> <delivered>", so bin/watch.sh can share it.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from .log import Post, Workspace, WatchkeeperError


@dataclass
class Cursor:
    acked: int = 0
    delivered: int = 0


def cursor_path(ws: Workspace, reader: str):
    return ws.cursor_dir / reader


def load(ws: Workspace, reader: str) -> Cursor:
    p = cursor_path(ws, reader)
    if not p.exists():
        return Cursor()
    try:
        acked, delivered = (int(x) for x in p.read_text(encoding="utf-8").split())
    except ValueError as exc:
        raise WatchkeeperError(f"cursor file {p} is damaged; it should hold two numbers") from exc
    return Cursor(acked, max(acked, delivered))


def save(ws: Workspace, reader: str, c: Cursor) -> None:
    ws.cursor_dir.mkdir(parents=True, exist_ok=True)
    p = cursor_path(ws, reader)
    tmp = p.with_name(p.name + ".tmp")
    tmp.write_text(f"{c.acked} {c.delivered}\n", encoding="utf-8")
    os.replace(tmp, p)


@dataclass
class Delivery:
    posts: list[Post]  # posts by others, complete or torn, in log order
    redelivered: set[int]  # start lines of posts shown before but not acknowledged
    end_line: int  # line to record as delivered
    own: int  # how many of the reader's own posts were passed over


def pending(ws: Workspace, reader: str) -> Delivery:
    """Everything after the acknowledged line that is ready to read.

    A post still being written (no end marker, nothing after it) is left for
    next time. A torn post (another heading began before it ended) is shown,
    flagged, so it cannot hide.
    """
    c = load(ws, reader)
    shown, redelivered, own = [], set(), 0
    end = c.acked
    for p in ws.posts(after_line=c.acked):
        if not p.complete and not p.torn:
            break
        if p.complete:
            end = p.end_line
        if p.author == reader:
            own += 1
            continue
        shown.append(p)
        if p.start_line <= c.delivered:
            redelivered.add(p.start_line)
    return Delivery(shown, redelivered, end, own)


def mark_delivered(ws: Workspace, reader: str, line: int) -> None:
    c = load(ws, reader)
    if line > c.delivered:
        save(ws, reader, Cursor(c.acked, line))


def acknowledge(ws: Workspace, reader: str) -> Cursor:
    """Move "acknowledged" up to what was last delivered, and no further."""
    c = load(ws, reader)
    c = Cursor(c.delivered, c.delivered)
    save(ws, reader, c)
    return c
