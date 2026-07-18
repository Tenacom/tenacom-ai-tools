#!/usr/bin/env python3
"""pr_review_cleanup — remove a PR review's local artifacts (shared helper).

Imported, never run, by pr-finalize and pr-cleanup — the two commands that wipe a
finished review's working files. It is the single home for both the wipe itself and
the /dev/tty interaction those commands drive it with, the way pr_review_lint.py is
the single home for the REVIEW.md grammar. pr-install copies it beside the commands,
so each imports it from its own directory; it carries no execute bit.

The wipe is exactly the inverse of what pr-review's preparation lays down: the
snapshot dir (.pr-review/), the run dir (.pr-review-run/), REVIEW.md, and the three
lines preparation appends to .git/info/exclude to hide them from git status. It is
idempotent — a missing artifact is simply not removed — and touches nothing
preparation did not create: the exclude file keeps git's own default comment header
and any line a human added, because only the three verbatim entries are pruned.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

STATE_DIR = ".pr-review"
RUN_DIR = ".pr-review-run"
REVIEW_NAME = "REVIEW.md"
POSTED_NAME = "posted.md"
# The exact lines pr-review appends to .git/info/exclude (its "hide every review
# artifact" step). Matched verbatim, so only preparation's own entries are pruned.
EXCLUDE_ENTRIES = (".pr-review/", ".pr-review-run/", "REVIEW.md")
EXCLUDE_LABEL = ".git/info/exclude entries"


class NoTerminal(Exception):
    """No interactive terminal was available to read a confirmation from.

    Raised by confirm() so each command can turn it into its own tailored message
    rather than share one generic string."""


def _exclude_hits(git_dir: Path) -> tuple[Path, list[str]]:
    """The exclude file and the lines it still carries from our set (maybe empty)."""
    excl = git_dir / "info" / "exclude"
    if not excl.is_file():
        return excl, []
    lines = excl.read_text().splitlines()
    return excl, [ln for ln in lines if ln in EXCLUDE_ENTRIES]


def plan_cleanup(top: Path, git_dir: Path) -> list[str]:
    """What run_cleanup would remove right now, as human labels, removing nothing.

    An empty list means the tree is already clean."""
    labels: list[str] = []
    if (top / STATE_DIR).is_dir():
        labels.append(f"{STATE_DIR}/")
    if (top / RUN_DIR).is_dir():
        labels.append(f"{RUN_DIR}/")
    if (top / REVIEW_NAME).exists():
        labels.append(REVIEW_NAME)
    _, hits = _exclude_hits(git_dir)
    if hits:
        labels.append(EXCLUDE_LABEL)
    return labels


def run_cleanup(top: Path, git_dir: Path) -> list[str]:
    """Delete the snapshot and run dirs, REVIEW.md, and prune preparation's own
    entries from .git/info/exclude. Idempotent; returns what was actually removed."""
    removed: list[str] = []
    for name in (STATE_DIR, RUN_DIR):
        d = top / name
        if d.is_dir():
            shutil.rmtree(d)
            removed.append(f"{name}/")
    review = top / REVIEW_NAME
    if review.exists():
        review.unlink()
        removed.append(REVIEW_NAME)
    excl, hits = _exclude_hits(git_dir)
    if hits:
        kept = [ln for ln in excl.read_text().splitlines()
                if ln not in EXCLUDE_ENTRIES]
        excl.write_text("\n".join(kept) + "\n" if kept else "")
        removed.append(EXCLUDE_LABEL)
    return removed


def review_posted(top: Path) -> bool:
    """Whether pr-finalize already posted this preparation (its posted.md marker)."""
    return (top / RUN_DIR / POSTED_NAME).exists()


def confirm(prompt: str) -> bool:
    """A y/N answer on the controlling terminal.

    Prefer /dev/tty so an irreversible action needs a real keystroke, not something a
    pipe or heredoc (`echo y | …`) can pre-answer; fall back to stdin only when it is
    itself interactive; raise NoTerminal when neither is. Two one-directional handles,
    NOT "r+": any read+write mode builds a BufferedRandom, whose constructor demands a
    seekable raw stream — and a tty is not seekable, so "r+" raises
    io.UnsupportedOperation (a subclass of OSError, which would mislabel the failure as
    "no terminal"; observed on WSL2)."""
    try:
        tty_in = open("/dev/tty", "r")
        tty_out = open("/dev/tty", "w")
    except OSError:
        if not sys.stdin.isatty():
            raise NoTerminal
        sys.stderr.write(prompt)
        sys.stderr.flush()
        return sys.stdin.readline().strip()[:1] in ("y", "Y")
    try:
        tty_out.write(prompt)
        tty_out.flush()
        answer = tty_in.readline().strip()
    finally:
        tty_in.close()
        tty_out.close()
    return answer[:1] in ("y", "Y")


def pause(prompt: str) -> bool:
    """Wait for Enter on the controlling terminal before a destructive follow-up.

    Returns True on Enter (go ahead), False on Ctrl-C or when there is no terminal to
    read from — the safe default for something that deletes: do nothing. Unlike
    confirm() this never falls back to stdin: a pause is a courtesy before a wipe, and
    a non-interactive run should simply skip the wipe, not consume a line of input."""
    try:
        tty_in = open("/dev/tty", "r")
        tty_out = open("/dev/tty", "w")
    except OSError:
        return False
    try:
        tty_out.write(prompt)
        tty_out.flush()
        tty_in.readline()
    except KeyboardInterrupt:
        return False
    finally:
        tty_in.close()
        tty_out.close()
    return True
