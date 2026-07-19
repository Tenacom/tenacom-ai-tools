"""pr_review_common — shared low-level code for the pr-review command family.

The single home for what every command needs and none should own: the
program-prefixed stderr messaging (log/die), the /dev/tty interaction
(confirm/pause), the subprocess plumbing (run, plus the git/gh wrappers that
die with context), and the canonical artifact names preparation lays down at
the repo root. Imported, never run, by the Python commands (pr-finalize,
pr-check, pr-cleanup, pr-assemble-rules) and by the sibling modules
pr_review_lint and pr_review_cleanup. pr-install copies it beside the
commands, so each imports it from its own directory; it carries no execute
bit.

Every message goes to stderr, prefixed "<prog>: " — stdout stays reserved for
each command's machine-readable output. The prefix is process-global state:
each command calls set_prog(PROG) once at startup, so every call site stays
die(msg)/log(msg) with no program name threaded through.
"""

from __future__ import annotations

import json
import subprocess
import sys
from typing import Any, NoReturn

# --- canonical artifact names -------------------------------------------------

# The names preparation creates at the repo root and every command resolves
# against. One home: commands build their own Path objects from these.
STATE_DIR_NAME = ".pr-review"      # the preparation snapshot dir
RUN_DIR_NAME = ".pr-review-run"    # the run dir (agent reports, posted markers)
REVIEW_NAME = "REVIEW.md"          # the review file, at the repo root
POSTED_NAME = "posted.md"          # pr-finalize's as-posted marker, in the run dir


# --- logging ------------------------------------------------------------------

_prog = "pr-review"  # overridden by each command's set_prog(PROG) at startup


def set_prog(name: str) -> None:
    """Set the program name log() and die() prefix messages with.

    Called once at each command's startup. Module state rather than a
    parameter, so the many call sites stay die(msg)/log(msg)."""
    global _prog  # noqa: PLW0603 — a documented, deliberate process-global (see module docstring)
    _prog = name


def log(msg: str) -> None:
    """Print msg to stderr, prefixed with the program name."""
    print(f"{_prog}: {msg}", file=sys.stderr)


def die(msg: str) -> NoReturn:
    """Print msg to stderr and exit with status 1."""
    log(msg)
    raise SystemExit(1)


# --- user interaction ---------------------------------------------------------

class NoTerminalError(Exception):
    """No interactive terminal was available to read a confirmation from.

    Raised by confirm() so each command can turn it into its own tailored message
    rather than share one generic string."""


def confirm(prompt: str) -> bool:
    """A y/N answer on the controlling terminal.

    Prefer /dev/tty so an irreversible action needs a real keystroke, not something a
    pipe or heredoc (`echo y | …`) can pre-answer; fall back to stdin only when it is
    itself interactive; raise NoTerminalError when neither is. Two one-directional handles,
    NOT "r+": any read+write mode builds a BufferedRandom, whose constructor demands a
    seekable raw stream — and a tty is not seekable, so "r+" raises
    io.UnsupportedOperation (a subclass of OSError, which would mislabel the failure as
    "no terminal"; observed on WSL2)."""
    try:
        tty_in = open("/dev/tty")  # noqa: SIM115, PTH123 — deliberate; see the docstring
        tty_out = open("/dev/tty", "w")  # noqa: SIM115, PTH123
    except OSError:
        if not sys.stdin.isatty():
            raise NoTerminalError from None
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
        tty_in = open("/dev/tty")  # noqa: SIM115, PTH123 — deliberate; see the docstring
        tty_out = open("/dev/tty", "w")  # noqa: SIM115, PTH123
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


# --- external processes -------------------------------------------------------

def run(*args: str, stdin: str | None = None,
        text: bool = True) -> subprocess.CompletedProcess[Any]:
    """subprocess.run with both output streams captured. Text mode by default;
    text=False yields raw bytes for a caller that must police the decoding
    itself (pr-assemble-rules reads git blobs that may not be valid UTF-8)."""
    return subprocess.run(args, input=stdin, text=text, capture_output=True, check=False)


def git(*args: str, what: str) -> str:
    """Run git, die with `what` as context on failure, return stripped stdout."""
    p = run("git", *args)
    if p.returncode != 0:
        die(f"{what} failed: {p.stderr.strip() or 'git error'}")
    return p.stdout.strip()


def gh(*args: str, what: str, stdin: str | None = None) -> str:
    """Run gh, die with `what` as context on failure, return stdout verbatim."""
    p = run("gh", *args, stdin=stdin)
    if p.returncode != 0:
        die(f"{what} failed: {p.stderr.strip() or 'gh error'}")
    return p.stdout


def gh_api_list(path: str, what: str) -> list[dict[str, Any]]:
    """GET a paginated array endpoint as one list. `--paginate` alone would
    concatenate the pages' arrays into invalid JSON, so each element is
    flattened to one raw JSON line instead (gh prints jq string results raw)."""
    out = gh("api", "--paginate", path, "--jq", ".[] | @json", what=what)
    return [json.loads(line) for line in out.splitlines() if line.strip()]
