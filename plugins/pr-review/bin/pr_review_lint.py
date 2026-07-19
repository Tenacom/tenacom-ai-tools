"""Grammar, model and linter for REVIEW.md — shared by pr-finalize and pr-check.

This module owns everything needed to read a curated REVIEW.md and decide
whether it is fit to post: the closed `###`/`##` grammar, the Block/Section
model, the diff-range parser, and a `lint()` pass that walks a parsed tree the
same way routing does but only collects Problems — never builds a payload and
never touches the network. pr-finalize imports it to lint before it posts;
pr-check imports it to lint on its own, offline. Keeping the two on one grammar
is the point: a file pr-check calls clean is a file pr-finalize will post.

A Problem carries a 1-based line and column so a batch sorts into file order and
each line is clickable in the VS Code terminal (`REVIEW.md:line:column`). The
lint is deliberately curation-aware — a fault is reported only where it would
actually reach GitHub: a bad link in an unchecked block posts nothing, so it is
left inert, exactly as routing leaves it inert. That is why the lint mirrors the
routing traversal rather than scanning the file blindly.
"""

from __future__ import annotations

import re
import sys

from pr_review_common import REVIEW_NAME

LINK = re.compile(r"\]\(\./([^)#]+)#(\d+)\)")  # target: ](./path#start)
END_L = re.compile(r"-L(\d+)\]")               # range end in the link TEXT
CHECKBOX = re.compile(r"^###\s+\[([ xX])\]")
PROSE_LINK = re.compile(r"\[([^\]]*)\]\(\./([^)]*)\)")  # a [text](./target) link in prose
BARE_LINE = re.compile(r"\d+\Z")                        # a relative target's fragment
TEXT_END_L = re.compile(r"-L(\d+)\Z")                   # range end at the tail of link TEXT

# The three positional sections REVIEW.md always carries (Problems, Observations,
# Pre-existing); a checked finding past the third is a grammar violation.
SECTION_COUNT = 3


# --- problems -----------------------------------------------------------------

class Problem:
    """One fault in REVIEW.md, anchored at a 1-based line and column.

    The anchor lets the batch be sorted into file order and each line clicked in
    the VS Code terminal (the `REVIEW.md:line:column` shape it linkifies). `msg`
    is the one-line statement; `hint`, when present, is the longer guidance,
    printed indented on its own line(s) so it is not read as another location."""

    __slots__ = ("col", "hint", "line", "msg")

    def __init__(self, line: int, col: int, msg: str, hint: str = "") -> None:
        self.line = line
        self.col = col
        self.msg = msg
        self.hint = hint


def bail_on_problems(problems: list[Problem], prog: str, note: str = "") -> None:
    """Report every collected problem in file order and exit; return if none.

    Each is a `REVIEW.md:line:column: message` diagnostic — the gcc shape the VS
    Code terminal turns into a clickable link — with any hint indented beneath
    it, then a one-line summary tagged with `prog` (the calling command) and, if
    given, `note` (what the caller did about it — pr-finalize appends "nothing
    posted", pr-check has nothing to add). The caller runs this before anything is
    posted or deleted, so exiting here leaves nothing half-done."""
    if not problems:
        return
    problems.sort(key=lambda p: (p.line, p.col))
    for p in problems:
        print(f"{REVIEW_NAME}:{p.line}:{p.col}: {p.msg}", file=sys.stderr)
        for hint_line in p.hint.splitlines():
            print(f"    {hint_line}", file=sys.stderr)
    n = len(problems)
    tail = f" — {note}" if note else ""
    print(f"{prog}: {n} problem{'s' if n != 1 else ''} in {REVIEW_NAME}{tail}",
          file=sys.stderr)
    raise SystemExit(1)


# --- model --------------------------------------------------------------------

class Block:
    """One ### finding: checkbox, optional location, prose, and its source lines."""

    __slots__ = (
        "checked",
        "end",
        "head_line",
        "link_col",
        "path",
        "prose",
        "prose_line",
        "start",
    )

    def __init__(self, checked: bool, path: str | None,
                 start: int | None, end: int | None, prose: str,
                 head_line: int, prose_line: int, link_col: int | None) -> None:
        self.checked = checked
        self.path = path
        self.start = start
        self.end = end
        self.prose = prose
        self.head_line = head_line    # 1-based line of the ### heading
        self.prose_line = prose_line  # 1-based line the (trimmed) prose starts on
        self.link_col = link_col      # 1-based column of the heading link's [, if located

    def location(self) -> tuple[str, int, int] | None:
        """The (path, start, end) triple when this finding is located, else None.

        A located finding carries all three (parse_review sets them together from
        the heading link, or leaves all three None); returning them as a unit lets
        a caller narrow once instead of re-checking each field against None."""
        if self.path is None or self.start is None or self.end is None:
            return None
        return self.path, self.start, self.end


class Section:
    """One ## section: ordinal, label, preamble, and its blocks."""

    __slots__ = (
        "blocks",
        "head_line",
        "label",
        "ordinal",
        "preamble",
        "preamble_line",
    )

    def __init__(self, ordinal: int, label: str, preamble: str,
                 blocks: list[Block], head_line: int, preamble_line: int) -> None:
        self.ordinal = ordinal
        self.label = label
        self.preamble = preamble
        self.blocks = blocks
        self.head_line = head_line          # 1-based line of the ## heading
        self.preamble_line = preamble_line  # 1-based line the preamble starts on


def _trim(lines: list[str], start: int) -> tuple[str, int]:
    """Join lines, dropping leading and trailing blank ones.

    `start` is the 1-based REVIEW.md line of lines[0]; the returned int is that
    line advanced past any dropped leading blanks, so a link's offset in the
    joined text maps back to its true line number."""
    i, j = 0, len(lines)
    while i < j and not lines[i].strip():
        i += 1
    while j > i and not lines[j - 1].strip():
        j -= 1
    return "\n".join(lines[i:j]), start + i


# --- the diff -----------------------------------------------------------------

def parse_diff_ranges(diff_text: str) -> dict[str, list[tuple[int, int]]]:
    """Changed (added-side) line ranges per path, from the canonical diff."""
    ranges: dict[str, list[tuple[int, int]]] = {}
    path: str | None = None
    for line in diff_text.splitlines():
        if line.startswith("+++ "):
            p = line[4:].strip()
            p = p.removeprefix("b/")
            path = None if p == "/dev/null" else p
        elif line.startswith("@@ ") and path is not None:
            m = re.search(r"\+(\d+)(?:,(\d+))?", line)
            if not m:
                continue
            start = int(m.group(1))
            length = int(m.group(2)) if m.group(2) is not None else 1
            if length > 0:
                ranges.setdefault(path, []).append((start, start + length - 1))
    return ranges


def in_diff(ranges: dict[str, list[tuple[int, int]]], path: str, line: int) -> bool:
    """Whether line falls within any changed range recorded for path."""
    return any(lo <= line <= hi for lo, hi in ranges.get(path, ()))


# --- parsing ------------------------------------------------------------------

def parse_review(text: str, problems: list[Problem]
                 ) -> tuple[str, int, list[Section]]:
    """Split REVIEW.md into its body and its ## sections.

    Frontmatter is skipped (the snapshot is the source of truth for pr/head).
    The body is everything up to the first ## heading. Each section carries its
    ordinal, its (possibly human-edited) heading text as the label, the preamble
    between the heading and its first ### block, and its blocks. Returns the body
    with its 1-based start line (so its links can be reported at the right line),
    then the sections. Any finding sitting above the first section is recorded
    into `problems`, one per stray block, rather than raised.
    """
    lines = text.splitlines()
    n = len(lines)
    i = 0

    if i < n and lines[i].strip() == "---":      # frontmatter
        i += 1
        while i < n and lines[i].strip() != "---":
            i += 1
        if i < n:
            i += 1

    body_start = i
    while i < n and not lines[i].startswith("## "):
        i += 1
    body_lines = lines[body_start:i]
    for k, ln in enumerate(body_lines):
        if ln.startswith("### "):
            problems.append(Problem(body_start + k + 1, 1,
                "a finding (### block) appears before the first section (## heading)",
                "Every finding must sit under one of the three sections; move it "
                "under one."))
    body, body_line = _trim(body_lines, body_start + 1)

    sections: list[Section] = []
    while i < n and lines[i].startswith("## "):
        head_line = i + 1
        label = lines[i][3:].strip()
        i += 1

        pre_start = i
        while i < n and not lines[i].startswith(("### ", "## ")):
            i += 1
        preamble, preamble_line = _trim(lines[pre_start:i], pre_start + 1)

        blocks: list[Block] = []
        while i < n and lines[i].startswith("### "):
            head = lines[i]
            b_head_line = i + 1
            i += 1
            cm = CHECKBOX.match(head)
            checked = bool(cm and cm.group(1) in ("x", "X"))
            lm = LINK.search(head)
            if lm:
                path: str | None = lm.group(1)
                start: int | None = int(lm.group(2))
                em = END_L.search(head)
                end: int | None = int(em.group(1)) if em else start
                # Anchor the diagnostic at the [ that opens the link text, not
                # the ]( where LINK matches — the link text is where the curator
                # reads and edits the location. (No ] inside link text, so the
                # last [ before the match opens it.)
                link_col: int | None = head.rfind("[", 0, lm.start()) + 1
            else:
                path = start = end = None
                link_col = None
            pr_start = i
            while i < n and not lines[i].startswith(("## ", "### ")):
                i += 1
            prose, prose_line = _trim(lines[pr_start:i], pr_start + 1)
            blocks.append(Block(checked, path, start, end, prose,
                                b_head_line, prose_line, link_col))

        sections.append(Section(len(sections) + 1, label, preamble, blocks,
                                head_line, preamble_line))

    return body, body_line, sections


# --- linting ------------------------------------------------------------------

def check_fragments(text: str, origin_line: int, problems: list[Problem]) -> None:
    """Record every relative code link in `text` whose fragment is not a bare
    line number — `./path#L52`, `./path#anchor` — anchored at its real line and
    column. `origin_line` is the 1-based REVIEW.md line `text` starts on. This is
    the validation half of the link grammar: pr-finalize's linkify_prose does the
    matching rewrite, and runs only after this has passed, so it can assume every
    fragment is bare. A fragmentless target (a whole-file link) is fine, and an
    absolute link (a curator-pasted permalink) never matches ./ at all."""
    for m in PROSE_LINK.finditer(text):
        link_text, target = m.group(1), m.group(2)
        if "#" not in target:
            continue
        _, _, frag = target.rpartition("#")
        if BARE_LINE.fullmatch(frag):
            continue
        before = text[:m.start()]
        line = origin_line + before.count("\n")
        col = m.start() - (before.rfind("\n") + 1) + 1
        problems.append(Problem(line, col,
            f"a relative code link, [{link_text}](./{target}), has a "
            f"fragment (#{frag}) that is not a bare line number",
            "#L… is the GitHub fragment form, not the relative one. Point "
            "it at a line as ./path#123, or at the whole file as ./path "
            "with no fragment at all."))


def lint(body: str, body_line: int, sections: list[Section],
         ranges: dict[str, list[tuple[int, int]]],
         problems: list[Problem]) -> None:
    """Collect every fault that would keep REVIEW.md from posting.

    Walks the tree the way routing does — so a fault is reported only where the
    text would actually reach GitHub — and appends to `problems` (parse_review
    has already added any finding sitting above the first section). Five checks:
    a code link whose fragment is not a bare line (in every posted string: the
    body, each checked block, each contributing preamble); a checked finding in
    a fourth-or-later section; a checked inline finding anchored outside the
    diff; and a checked finding folded under an unlabeled section heading. The
    caller bails on a non-empty batch before routing, so routing may then assume
    a valid tree."""
    check_fragments(body, body_line, problems)  # the body always posts

    for s in sections:
        # A fourth (or later) section is a grammar violation, but only when it
        # actually carries something to post; reported once, at its ## heading.
        if s.ordinal > SECTION_COUNT:
            if any(b.checked for b in s.blocks):
                problems.append(Problem(s.head_line, 1,
                    f"a checked finding sits under section #{s.ordinal} "
                    f"(«{s.label}»), but the grammar has exactly three "
                    "sections",
                    "The three sections are Problems, Observations, Pre-existing, "
                    "in that order. Keep all three ## headings, even if empty."))
            continue

        folds_here = False
        for b in s.blocks:
            if not b.checked:
                continue

            # Every checked block's prose posts (inline body or folded), so its
            # links are checked here; an unchecked block's are left inert.
            check_fragments(b.prose, b.prose_line, problems)

            # Sections 1 & 2, located: inline, and both endpoints must be in the
            # diff. GitHub anchors on b.end (b.start as start_line for a range)
            # and resolves each endpoint against the diff, so an end line past
            # the changed hunk 422s the all-or-nothing post ("Line could not be
            # resolved") even when the start is in.
            loc = b.location()
            if loc is not None and s.ordinal in (1, 2):
                path, start, end = loc
                outside = [ln for ln in sorted({start, end})
                           if not in_diff(ranges, path, ln)]
                if outside:
                    if start == end:
                        where = f"line {start}, which is"
                    else:
                        nums = " and ".join(str(ln) for ln in outside)
                        plural = "s" if len(outside) > 1 else ""
                        verb = "are" if len(outside) > 1 else "is"
                        where = (f"lines {start}-{end}, whose line{plural} "
                                 f"{nums} {verb}")
                    problems.append(Problem(b.head_line, b.link_col or 1,
                        f"a checked finding in section «{s.label}» points at "
                        f"{path} {where} outside this PR's diff",
                        "Inline comments must land on changed lines. If it is "
                        "pre-existing, move it to the third (Pre-existing) section; if "
                        "its anchor is stale, re-prepare. Then re-run."))
                continue

            # Everything else folds: section 3 (any), sections 1 & 2 locationless.
            folds_here = True

        # A section whose checked findings fold needs a label to fold them under;
        # reported once, at its ## heading, when something actually folds here.
        if folds_here and not s.label:
            problems.append(Problem(s.head_line, 1,
                f"section #{s.ordinal} has a checked finding to fold but its ## "
                "heading has no text to use as a label",
                "Label the heading, then re-run."))

        # A contributing section's preamble folds into the body ahead of its
        # findings, so it posts too — check its links, matching route.
        if folds_here and s.preamble:
            check_fragments(s.preamble, s.preamble_line, problems)
