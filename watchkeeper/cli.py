"""The `watchkeeper` (or `wk`) command."""

from __future__ import annotations

import argparse
import os
import sys
import time
from datetime import timedelta
from importlib import resources

from . import __version__
from . import cursor as cur
from .lint import check_heading, find_secrets, lint_workspace
from .log import (
    ADMISSION_TYPES,
    END,
    FOOT_MARKER,
    LANES_FILE,
    NAME_RE,
    SEP,
    TS_RE,
    Workspace,
    WatchkeeperError,
    format_heading,
    now_utc,
    parse_ts,
)
from .status import format_line, open_admissions, read_status, reserve

EXIT_OK, EXIT_REFUSED, EXIT_TIMEOUT = 0, 1, 2
RETRY_WINDOW = timedelta(minutes=10)  # an identical post within this window is treated as a retry


def log_head() -> str:
    return resources.files("watchkeeper").joinpath("log_head.md").read_text(encoding="utf-8")


# ---------------------------------------------------------------- init


def cmd_init(ws: Workspace, args) -> int:
    lanes = [x.strip().upper() for x in args.lanes.split(",") if x.strip()]
    bad = [x for x in lanes if not NAME_RE.match(x) or x in ("COORDINATOR", "OWNER")]
    if not lanes or bad:
        raise WatchkeeperError(f"lane names must be upper-case words, not COORDINATOR or OWNER: {bad or 'none given'}")
    if ws.log.exists():
        raise WatchkeeperError(f"{ws.log} already exists; refusing to overwrite it")
    ws.root.mkdir(parents=True, exist_ok=True)
    ws.status_dir.mkdir(exist_ok=True)
    ws.cursor_dir.mkdir(parents=True, exist_ok=True)
    (ws.state / LANES_FILE).write_text("\n".join(lanes) + "\n", encoding="utf-8")
    ws.log.write_text(log_head().rstrip("\n") + "\n\n" + FOOT_MARKER + "\n", encoding="utf-8")
    ts = now_utc()
    for lane in lanes:
        p = ws.status_dir / f"{lane}.md"
        if not p.exists():
            p.write_text(format_line("NONE", ts) + "\n\nNo reservation yet.\n", encoding="utf-8")
    print(f"created {ws.log.name}, status/ for {', '.join(lanes)}, and {ws.state.name}/ in {ws.root}")
    return EXIT_OK


# ---------------------------------------------------------------- post


def read_body(args) -> str:
    if args.body_file:
        if args.body_file == "-":
            return sys.stdin.read()
        with open(args.body_file, encoding="utf-8") as f:
            return f.read()
    return args.body or ""


def cmd_post(ws: Workspace, args) -> int:
    author = args.author
    to = args.to.upper() if args.to else None
    kind = args.type.upper()
    details = [d.strip() for d in args.details]
    body = read_body(args).strip("\n")
    lanes = ws.lanes()

    for d in details:
        if not d or SEP.strip() in d or "\n" in d:
            raise WatchkeeperError("a heading field may not be empty or contain an em dash or a new line")
    for line in body.split("\n"):
        if line.startswith("## ") or line.strip() == END or line.strip() == FOOT_MARKER:
            raise WatchkeeperError("the body may not contain a heading or a marker line; indent it to quote it")

    with ws.locked():
        # Everything below is read after the lock is held.
        posts = ws.posts()
        ts = now_utc()
        heading = format_heading(author, to, kind, details, ts)
        problems = check_heading(heading, lanes)
        if problems:
            raise WatchkeeperError("refused: " + "; ".join(problems))
        secrets = find_secrets(heading + "\n" + body)
        if secrets:
            kinds = ", ".join(sorted({k for _, k in secrets}))
            raise WatchkeeperError(f"refused: the post contains something that looks like a {kinds}. Remove it and rotate it.")

        complete = [p for p in posts if p.complete]
        if complete:
            last_ts = complete[-1].fields["ts"] if complete[-1].fields else ""
            if TS_RE.match(last_ts) and parse_ts(ts) + timedelta(seconds=120) < parse_ts(last_ts):
                raise WatchkeeperError("refused: this machine's clock is behind the last post; fix the clock first")

        # A retry after an unknown outcome must not post twice. A deliberate
        # repeat later on is a new post, so this only looks back a few minutes.
        mine = [p for p in complete if p.author == author]
        if mine:
            last = mine[-1]
            same_heading = last.heading.rsplit(SEP, 1)[0] == heading.rsplit(SEP, 1)[0]
            last_ts = last.fields["ts"] if last.fields else ""
            recent = TS_RE.match(last_ts) and parse_ts(ts) - parse_ts(last_ts) <= RETRY_WINDOW
            if same_heading and recent and "\n".join(last.body).strip("\n") == body:
                print(f"already posted at line {last.start_line}: {last.heading}")
                return EXIT_OK

        # The latest post addressed to a lane binds it. Anything else sent to an
        # admitted lane silently replaces its permission.
        if author == "COORDINATOR" and kind not in ADMISSION_TYPES and not args.force:
            active = open_admissions(ws)
            hit = sorted(active) if to == "ALL LANES" else ([to] if to in active else [])
            if hit:
                raise WatchkeeperError(
                    f"refused: {', '.join(hit)} has an open admission, and this post would replace it as the "
                    "lane's binding post. Wait until the case closes, or use --force and then re-post the "
                    "full ADMITTED or ENTRY OPEN."
                )

        text = ws.log.read_text(encoding="utf-8")
        lead = "" if text.endswith("\n") else "\n"
        if text.rstrip("\n").split("\n")[-1].strip() != FOOT_MARKER:
            lead += "\n"  # a blank line between posts, for people reading the file
        ws.append(lead + heading + "\n" + (body + "\n" if body else "") + END + "\n")

        # Read back: the post must be there, whole, exactly once.
        check = [p for p in ws.posts() if p.heading == heading]
        if len(check) != 1 or not check[0].complete:
            raise WatchkeeperError("posted, but the read-back failed; run 'wk lint' before doing anything else")
    print(f"posted at line {check[0].start_line}: {heading}")
    return EXIT_OK


# ---------------------------------------------------------------- read and watch


def show(d: cur.Delivery, reader: str) -> None:
    for p in d.posts:
        flags = []
        if p.start_line in d.redelivered:
            flags.append("REDELIVERED: shown before, not yet acknowledged")
        if p.torn:
            flags.append("TORN: this post was cut short; ask its author to read back and re-post")
        for flag in flags:
            print(f"[{flag}]")
        print(p.heading)
        for line in p.body:
            print(line)
        print()
    print(f"{len(d.posts)} post(s). When you have dealt with them, run: wk read --as {reader} --ack")


def cmd_read(ws: Workspace, args) -> int:
    reader = args.reader
    if args.ack:
        c = cur.acknowledge(ws, reader)
        print(f"acknowledged up to line {c.acked}")
        return EXIT_OK
    if args.headings:
        c = cur.load(ws, reader)
        for p in ws.posts(after_line=c.acked):
            print(f"{p.start_line}: {p.heading}{'' if p.complete else '  [INCOMPLETE]'}")
        return EXIT_OK
    d = cur.pending(ws, reader)
    if not d.posts:
        if d.end_line:
            cur.mark_delivered(ws, reader, d.end_line)
        print("nothing new")
        return EXIT_OK
    show(d, reader)
    cur.mark_delivered(ws, reader, d.end_line)
    return EXIT_OK


def silent_lanes(ws: Workspace, minutes: int) -> list[str]:
    now = parse_ts(now_utc())
    last: dict[str, str] = {}
    for p in ws.posts():
        f = p.fields
        if p.complete and f and TS_RE.match(f["ts"]):
            last[f["author"]] = f["ts"]
    out = []
    for lane in ws.lanes():
        if lane not in last:
            out.append(f"SILENT {lane} never posted")
        elif now - parse_ts(last[lane]) >= timedelta(minutes=minutes):
            out.append(f"SILENT {lane} since {last[lane]}")
    return out


def cmd_watch(ws: Workspace, args) -> int:
    reader = args.reader
    deadline = time.monotonic() + args.timeout
    while True:
        d = cur.pending(ws, reader)
        if d.posts:
            show(d, reader)
            cur.mark_delivered(ws, reader, d.end_line)
            return EXIT_OK
        if time.monotonic() >= deadline:
            break
        time.sleep(min(args.interval, max(0.0, deadline - time.monotonic())))
    print(f"no new post in {args.timeout}s")
    for line in silent_lanes(ws, args.silent_after):
        print(line)
    return EXIT_TIMEOUT


# ---------------------------------------------------------------- lint and status


def cmd_lint(ws: Workspace, args) -> int:
    problems = lint_workspace(ws)
    for p in problems:
        print(p)
    if problems:
        print(f"{len(problems)} problem(s)")
        return EXIT_REFUSED
    print(f"clean: {len(ws.posts())} post(s), {len(ws.lanes())} lane(s)")
    return EXIT_OK


def cmd_status(ws: Workspace, args) -> int:
    if args.action == "set":
        if not args.lane or not args.op:
            raise WatchkeeperError("usage: wk status set <LANE> <OP-ID or NONE>")
        line = reserve(ws, args.lane.upper(), args.op.upper())
        print(f"{args.lane.upper()}: {line}")
        return EXIT_OK
    busy = []
    for lane in ws.lanes():
        s = read_status(ws, lane)
        if s.error:
            print(f"{lane:<14} BUSY      {s.error}")
            busy.append(lane)
        else:
            print(f"{lane:<14} {s.op:<9} since {s.ts}")
            if s.busy:
                busy.append(lane)
    active = open_admissions(ws)
    for lane, op in sorted(active.items()):
        print(f"open admission: {lane} for {op}")
    print("environment: " + (f"BUSY ({', '.join(busy)})" if busy else "FREE"))
    return EXIT_OK


# ---------------------------------------------------------------- entry point


def build_parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--dir", help="workspace directory (default: $WATCHKEEPER_DIR or the current directory)")

    who = argparse.ArgumentParser(add_help=False)
    who.add_argument("--as", dest="reader", default=os.environ.get("WATCHKEEPER_AS"),
                     help="who you are: COORDINATOR, OWNER, or a lane name (default: $WATCHKEEPER_AS)")

    parser = argparse.ArgumentParser(prog="wk", description="Watchkeeper: a lane coordinator for AI agents.")
    parser.add_argument("--version", action="version", version=f"watchkeeper {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("init", parents=[common], help="create a log, status files, and cursors")
    p.add_argument("--lanes", required=True, help="comma-separated lane names, for example ALPHA,BETA")

    p = sub.add_parser("post", parents=[common, who], help="append one post, stamped with the clock")
    p.add_argument("--to", help="addressee: a lane, COORDINATOR, OWNER, or 'ALL LANES'")
    p.add_argument("type", help="post type, for example REQUEST or 'ENTRY OPEN'")
    p.add_argument("details", nargs="*", help="heading fields after the type, for example OP-0001")
    p.add_argument("--body", help="the post body (plain text)")
    p.add_argument("--body-file", help="read the body from a file, or '-' for standard input")
    p.add_argument("--force", action="store_true", help="post to an admitted lane anyway")

    p = sub.add_parser("read", parents=[common, who], help="show posts after your cursor")
    p.add_argument("--ack", action="store_true", help="acknowledge everything last shown to you")
    p.add_argument("--headings", action="store_true", help="list every heading after your cursor, your own included")

    p = sub.add_parser("watch", parents=[common, who], help="wait for a post from someone else")
    p.add_argument("--timeout", type=int, default=1500, help="seconds to wait (default 1500)")
    p.add_argument("--interval", type=float, default=5.0, help="seconds between checks (default 5)")
    p.add_argument("--silent-after", type=int, default=120, help="minutes before a quiet lane is reported (default 120)")

    sub.add_parser("lint", parents=[common], help="check the log and status files")

    p = sub.add_parser("status", parents=[common], help="show reservations, or set your own")
    p.add_argument("action", nargs="?", choices=["show", "set"], default="show")
    p.add_argument("lane", nargs="?")
    p.add_argument("op", nargs="?")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    ws = Workspace(args.dir)
    try:
        if args.command in ("post", "read", "watch"):
            if not args.reader:
                raise WatchkeeperError("say who you are with --as (or set WATCHKEEPER_AS)")
            args.reader = args.reader.upper()
            args.author = args.reader
            known = ws.lanes() + ["COORDINATOR", "OWNER"]
            if args.reader not in known:
                raise WatchkeeperError(f"unknown name {args.reader!r}; known: {', '.join(known)}")
        handler = {
            "init": cmd_init, "post": cmd_post, "read": cmd_read,
            "watch": cmd_watch, "lint": cmd_lint, "status": cmd_status,
        }[args.command]
        return handler(ws, args)
    except WatchkeeperError as exc:
        print(f"wk: {exc}", file=sys.stderr)
        return EXIT_REFUSED
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    sys.exit(main())
