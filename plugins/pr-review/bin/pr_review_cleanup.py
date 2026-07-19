#!/usr/bin/env python3
"""pr_review_cleanup — remove a PR review's local artifacts (shared helper).

Imported, never run, by pr-finalize and pr-cleanup — the two commands that wipe a
finished review's working files. It is the single home for the wipe itself, the way
pr_review_lint.py is the single home for the REVIEW.md grammar (the /dev/tty
interaction the commands drive it with lives in pr_review_common). pr-install
copies it beside the commands, so each imports it from its own directory; it
carries no execute bit.

The wipe is exactly the inverse of what pr-review's preparation lays down: the
snapshot dir (.pr-review/), the run dir (.pr-review-run/), REVIEW.md, and the three
lines preparation appends to .git/info/exclude to hide them from git status. It is
idempotent — a missing artifact is simply not removed — and touches nothing
preparation did not create: the exclude file keeps git's own default comment header
and any line a human added, because only the three verbatim entries are pruned.
"""

from __future__ import annotations

import shutil
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

from pr_review_common import (
    POSTED_NAME,
    REVIEW_NAME,
    RUN_DIR_NAME,
    STATE_DIR_NAME,
)

# The exact lines pr-review appends to .git/info/exclude (its "hide every review
# artifact" step). Matched verbatim, so only preparation's own entries are pruned.
EXCLUDE_ENTRIES = (f"{STATE_DIR_NAME}/", f"{RUN_DIR_NAME}/", REVIEW_NAME)
EXCLUDE_LABEL = ".git/info/exclude entries"


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
    if (top / STATE_DIR_NAME).is_dir():
        labels.append(f"{STATE_DIR_NAME}/")
    if (top / RUN_DIR_NAME).is_dir():
        labels.append(f"{RUN_DIR_NAME}/")
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
    for name in (STATE_DIR_NAME, RUN_DIR_NAME):
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
    return (top / RUN_DIR_NAME / POSTED_NAME).exists()
