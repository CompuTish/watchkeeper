"""Checks for headings, timestamps, vocabulary, torn posts, and secrets."""

from __future__ import annotations

import re
from datetime import timedelta

from .log import (
    NAME_RE,
    OP_RE,
    TS_RE,
    VOCABULARY,
    WINDOW_RE,
    Post,
    Workspace,
    now_utc,
    parse_heading,
    parse_ts,
)

# Words that have been misread as instructions. "stop" was once parsed as a
# halt for a lane that was never meant to halt. Use WAIT or HOLD instead.
BANNED_HEADING_WORDS = re.compile(r"\b(stop|stopped|halt|kill)\b", re.IGNORECASE)

# Near-misses of the entry trigger. Lanes match ENTRY OPEN exactly, so a
# paraphrase is worse than nothing: it looks like permission and is not.
ENTRY_PARAPHRASE = re.compile(r"\b(entry[\s_-]*open|open[\s_-]*entry|entry[\s_-]*opened)\b", re.IGNORECASE)

SECRET_PATTERNS = [
    ("private key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("cloud access key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("source-host token", re.compile(r"\b(gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|glpat-[A-Za-z0-9_-]{20,})")),
    ("API key", re.compile(r"\b(sk-[A-Za-z0-9_-]{20,}|AIza[0-9A-Za-z_-]{30,})")),
    ("chat token", re.compile(r"\bxox[abposr]-[A-Za-z0-9-]{10,}")),
    ("JSON web token", re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}")),
    ("credentials in a URL", re.compile(r"\b[a-z][a-z0-9+.-]*://[^\s/:@]+:[^\s/@]+@")),
    ("password or secret assignment", re.compile(r"\b(password|passwd|pwd|secret|api[_-]?key|token)\s*[:=]\s*[\"']?[^\s\"'<>]{6,}", re.IGNORECASE)),
]

CLOCK_SKEW = timedelta(seconds=120)


def find_secrets(text: str) -> list[tuple[int, str]]:
    """Return (line number, kind) for each secret-shaped string. Never the value."""
    hits = []
    for n, line in enumerate(text.split("\n"), start=1):
        for kind, rx in SECRET_PATTERNS:
            if rx.search(line):
                hits.append((n, kind))
    return hits


def check_heading(heading: str, lanes: list[str]) -> list[str]:
    """Problems with one heading, or [] if it is well formed."""
    f = parse_heading(heading)
    if f is None:
        return ["not a post heading: expected '## AUTHOR[ → ADDRESSEE]: TYPE — ... — UTC'"]
    errs = []
    author, to, kind, details, ts = f["author"], f["to"], f["type"], f["details"], f["ts"]
    if author not in ("COORDINATOR", "OWNER") and author not in lanes:
        errs.append(f"unknown author {author!r}; known lanes: {', '.join(lanes)}")
    if to is not None and to not in ("COORDINATOR", "OWNER", "ALL LANES") and to not in lanes:
        errs.append(f"unknown addressee {to!r}")
    if kind not in VOCABULARY:
        if ENTRY_PARAPHRASE.search(kind):
            errs.append(f"{kind!r} is a paraphrase of the entry trigger; write exactly 'ENTRY OPEN'")
        else:
            errs.append(f"{kind!r} is not in the vocabulary: {', '.join(VOCABULARY)}")
    else:
        role = author if author in ("COORDINATOR", "OWNER") else "LANE"
        if role not in VOCABULARY[kind]:
            errs.append(f"{kind} may not be posted by {author}")
    if kind == "ENTRY OPEN":
        if to is None or to not in lanes:
            errs.append("ENTRY OPEN must be addressed to exactly one lane")
        if len(details) != 2 or not OP_RE.match(details[0]) or not WINDOW_RE.match(details[1]):
            errs.append("ENTRY OPEN takes exactly: ENTRY OPEN — <OP-ID> — <HH:MMZ-HH:MMZ>")
    if kind in ("REQUEST", "ADMITTED", "ENTERED", "RELEASED", "WITHDRAWN", "ACCEPTED+RELEASED"):
        if not details or not OP_RE.match(details[0]):
            errs.append(f"{kind} must name its operation first, for example '{kind} — OP-0001'")
    for d in details:
        if ENTRY_PARAPHRASE.search(d) and kind != "ENTRY OPEN":
            errs.append("do not write the entry trigger inside another post's heading")
    if BANNED_HEADING_WORDS.search(heading):
        errs.append("headings may not say stop, halt, or kill; use WAIT or HOLD")
    if not TS_RE.match(ts):
        errs.append(f"timestamp {ts!r} must be clock time in the form YYYY-MM-DDTHH:MM:SSZ")
    return errs


def reposted(torn: Post, later: list[Post]) -> bool:
    """A torn post is dealt with once its author re-posts the same heading in full."""
    key = torn.heading.rsplit(" — ", 1)[0]
    return any(p.complete and p.heading.rsplit(" — ", 1)[0] == key for p in later)


def lint_posts(posts: list[Post], lanes: list[str], now: str | None = None) -> list[str]:
    """Problems across a run of posts: headings, torn posts, clock order, secrets."""
    now_dt = parse_ts(now or now_utc())
    errs = []
    previous = None
    for i, p in enumerate(posts):
        where = f"line {p.start_line}"
        for e in check_heading(p.heading, lanes):
            errs.append(f"{where}: {e}")
        if p.torn and not reposted(p, posts[i + 1:]):
            errs.append(f"{where}: torn post (a new heading began before its end marker); its author should re-post it in full")
        f = p.fields
        if f and TS_RE.match(f["ts"]):
            ts = parse_ts(f["ts"])
            if ts > now_dt + CLOCK_SKEW:
                errs.append(f"{where}: timestamp is in the future, so it was typed, not taken from the clock")
            if previous and ts + CLOCK_SKEW < previous:
                errs.append(f"{where}: timestamp is earlier than the post before it, so it was typed, not taken from the clock")
            previous = ts if previous is None else max(previous, ts)
        for n, kind in find_secrets(p.text()):
            errs.append(f"line {p.start_line + n - 1}: looks like a {kind}; remove it and rotate it")
    return errs


def lint_workspace(ws: Workspace, now: str | None = None) -> list[str]:
    from .status import read_status

    lanes = ws.lanes()
    posts = ws.posts()
    errs = lint_posts(posts, lanes, now)
    # An unfinished post at the very end may still be being written; anything
    # else without an end marker is reported.
    for p in posts[:-1]:
        if not p.complete and not p.torn:
            errs.append(f"line {p.start_line}: post has no end marker")
    if posts and not posts[-1].complete:
        errs.append(f"line {posts[-1].start_line}: last post has no end marker (still being written, or torn)")
    for lane in lanes:
        if not NAME_RE.match(lane):
            errs.append(f"lanes file: {lane!r} is not an upper-case name")
        st = read_status(ws, lane)
        if st.error:
            errs.append(f"status/{lane}.md: {st.error}")
    return errs
