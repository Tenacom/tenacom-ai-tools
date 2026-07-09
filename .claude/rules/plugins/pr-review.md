---
description: Development rules and durable contracts for the pr-review plugin.
paths:
  - "plugins/pr-review/**"
---

# pr-review plugin — development rules

These rules orient development of the `pr-review` plugin and pin the invariants that
future work must respect. **`plugins/pr-review/skills/run/SKILL.md` is the
authoritative spec** — when this file and `SKILL.md` disagree about review behaviour,
`SKILL.md` wins, and this file should be corrected.

## What it is

A PR-review pipeline for GitHub repos built on Claude Code: a six-agent parallel review
that writes a structured `REVIEW.md` — body = the PR-level review comment; `###`-headed
blocks = findings, **posted only when a human checks their checkbox** — reviewed against
the full local source (not just the diff). The review runs **sandboxed with zero network, zero prompts,
zero reliance on the Task notification channel**; everything network- or write-side lives
outside the sandbox, in companion commands — `pr-review` (bash) prepares and launches,
`pr-finalize` (Python) posts, and `pr-assemble-rules` (Python) sources the rule set from the
base branch during preparation. The whole thing is distributed as a Claude Code plugin named
`pr-review`, installed from a private marketplace.

## Canonical names — do not drift

One scheme. Both end-user commands are `pr-<verb>`. The command `pr-review` deliberately
equals the plugin name and the skill namespace stem; these are separate namespaces (a PATH
executable, a plugin id, a skill prefix) so there is no collision, and the entry-point
command sharing the plugin name is a coherence win. `pr-assemble-rules` is a third `pr-<verb>`
binary but **not** an end-user command — it is an internal prep helper `pr-review` calls (see
Base-sourced rule set); it shares the naming and the PATH shim, nothing more.

| Thing                        | Canonical name           |
| ---------------------------- | ------------------------ |
| Prepare/launch command       | `pr-review`              |
| Post command                 | `pr-finalize`            |
| Rule-set helper (internal)   | `pr-assemble-rules`      |
| Review skill invocation      | `/pr-review:run`         |
| Review skill `name:` / dir   | `run` / `skills/run/`    |
| Snapshot dir (repo root)     | `.pr-review/`            |
| Base rule set (in snapshot)  | `.pr-review/rules/`      |
| Run dir (repo root)          | `.pr-review-run/`        |

`REVIEW.md` is uppercase and is not a `pr-review` token. The `.git/info/exclude` list a
prepared repo carries is exactly three entries: `.pr-review/`, `.pr-review-run/`,
`REVIEW.md`. Plugin-delivered skills are invoked `/<plugin>:<name>`, so the review is
`/pr-review:run` everywhere — `pr-review`'s launcher and the skill's self-references must
stay in lockstep (the "worked hand-installed, broke after packaging" trap).

## Plugin layout

All component dirs live at the plugin root; only `plugin.json` sits under `.claude-plugin/`.

```text
plugins/pr-review/
├── .claude-plugin/plugin.json   # name "pr-review"; version OMITTED (rolling/SHA)
├── bin/                         # added to the Bash-tool PATH while the plugin is enabled
│   ├── pr-review                #   prepare + launch (bash) — launcher execs /pr-review:run
│   ├── pr-finalize              #   post (Python 3, stdlib only)
│   ├── pr-assemble-rules        #   base-sourced rule set (Python 3, stdlib only) — prep helper
│   └── install-shims            #   PATH bootstrap (bash, self-locating)
├── skills/
│   ├── run/SKILL.md             #   the review — name: run → /pr-review:run; THE SPEC
│   └── install/SKILL.md         #   /pr-review:install — thin trigger for install-shims
├── hooks/hooks.json             #   SessionStart → "${CLAUDE_PLUGIN_ROOT}"/bin/install-shims
└── README.md
```

The four `bin/` files must be committed mode `755` (git tracks the bit; some output mounts
drop it). The docs' "hooks not firing → `chmod +x`" symptom is this.

## Hard contracts — must hold

### REVIEW.md

- Three lexical rules. `###` heading = checkbox + run + agent + optional relative link.
- The checkbox is the curation primitive: **only checked findings post**. Unwanted posting
  is unreachable by construction.
- Finding identity = agent + location.
- Three positional `##` sections, **always all present even when empty** (Problems /
  Observations / Pre-existing — written in the PR's language). A `##` heading's text is the
  verbatim fold label; a section may carry a preamble copied verbatim. A Pre-existing fix reads
  identically to any other fix (no scheduling preamble).
- Section-dependent anchor lint. One diff parse, two consumers (`pr-review`, `pr-finalize`).

### Finding prose — concise by contract

A finding states the defect, never the code (`SKILL.md`'s **defect-not-code rule**, in the
`###` blocks section): what is wrong, what triggers it, the consequence — said plainly in
a sentence or two, ahead of the fix, with evidence from elsewhere entering as one permalinked
clause. Three placements are deliberate and must not drift:

- The rule lives in the **block-format rules**, not the Voice section — voice governs
  concept-teaching only (glossing unfamiliar concepts in place; never re-explaining the
  author's own change back to them), and the defect-not-code rule binds the block format
  itself, whatever the voice says.
- **Assembly (SKILL step 7) distills, never transcribes.** Lane reports carry the full
  substantiation chain _for the validators_ — that is correct and must stay; the chain's
  human-facing residue is the conclusion plus the minimal decisive evidence, and the rest
  remains in the run directory for post-mortem. Do not "fix" verbosity by thinning lane
  reports: it would starve validation.
- Born of field feedback: early reviews narrated the anchored code paragraph by paragraph,
  and the human rewrote practically every finding before posting. Verbosity here is a
  defect, not thoroughness — never trade it back for "more evidence in `REVIEW.md`".

### Verdict and Observations — commit, never shrug

Same disease as finding verbosity, one level up: the model discharging findings without
committing to them. Also field feedback — early verdicts recapped the change back to its
author and narrated every finding up to three times (verdict, status-table Note, block),
and early Observations all ended in "up to you". Two contracts, both in `SKILL.md`:

- **The verdict is a judgment, never evidence** (The review file → Body): a hard word
  ceiling, no recap of the change (not even as praise or as proof of the verdict), no
  finding previews, no severity vocabulary, obstacles named by area and stake only. The
  load-bearing rationale is the **posting leak**, not style: the body posts unconditionally
  as the PR-level comment while blocks post only when checked, so a finding narrated in the
  verdict — or in a Note, which is why the Note is **parasitic on its block** (name what is
  unmet, point by location link text, add nothing the block says) — escapes the checkbox
  gate, the design's central guarantee. Keep that rationale attached to the rule; the word
  ceiling alone would be gamed again (the "one to three sentences" bound was, via
  colon-and-dash mega-sentences).
- **Observations carry a recommendation** (`###` blocks + Classification): the alternatives,
  the review's pick with its reason, then a question that asks _which alternative_, never
  _whether to bother_ — "fix it or leave it?" is a Problem wearing a question mark. "Both
  are fine" / "up to you" / "a matter of taste" are banned like severity labels: a stakeless
  question selects for the zero-effort answer and launders the issue into "reviewed and
  deemed optional". Upstream of format, classification: deviations from a clear dominant
  convention are Problems (one correct fix — follow the pattern); Observation status is
  reserved for genuine splits, scoping, and real design trade-offs, and agent 3's charter
  says so at the source so findings are not pre-softened at generation. The worked example's
  Observation blocks model the recommendation shape — do not let "either is fine" back into
  the example, because the example is what the model imitates.

### Language and strings (I18N)

- **`REVIEW.md` is written in the PR's language** — the original design intent, restored. The
  spec (`SKILL.md`) and every agent communicate in **English**; only `REVIEW.md` output carries
  the PR's language. Do not reintroduce a project's house language into the spec or the agents.
- **Load-bearing literals come from a glossary**, never improvised per run: the three section
  headings, the status faux-heading (`status.heading`), and the status table's outcome labels
  and column headers. Free prose is translated directly; only these are pinned, because the
  merge recreates missing `##` headings and a human navigates by stable labels.
- **Built-in glossaries: `en`, `it`, `es`** (defined verbatim in `SKILL.md`). Other languages
  are **pluggable**, in the consuming repo, at `.claude/pr-review/strings.<code>.json` (ISO 639-1
  code) — the plugin ships none (plugins cannot ship rules to users; see Dead ends). A project
  file present for a built-in code overrides the built-in; absent both, the model translates the
  English glossary and flags it as improvised. The override is **base-sourced** like the rest of
  the rule set (see Base-sourced rule set): the skill reads it from the preparation's copy at
  `.pr-review/rules/.claude/pr-review/strings.<code>.json`, not the checkout, so a PR cannot
  rewrite the labels the review is pinned to.
- **The posting path is language-agnostic by construction** — `pr-finalize` routes by section
  ordinal and the `^###\s+\[([ xX])\]` checkbox, never by heading text — so glossary changes need
  no code change there. Keep it that way: never make `pr-finalize` or `pr-review` key on any
  natural-language string.
- **Built-in glossaries are embedded in `SKILL.md`, not JSON files in the skill dir** —
  deliberately, against the (tempting) DRY instinct of one file mechanism for built-in and
  pluggable alike. Two reasons: a skill cannot reliably locate its own directory (see Dead ends →
  Skill self-location; `${CLAUDE_PLUGIN_ROOT}` is still on the verify list), and the `en` reference
  is needed **every run** as the fallback anchor, so it must be guaranteed in-context, never behind
  a Read that can fail on a bad plugin root. The override files escape this because they reach the
  skill as a **repo-root-relative snapshot path** (`.pr-review/rules/.claude/pr-review/strings.<code>.json`,
  base-sourced by prep) — reliable, the same read as the rest of the assembled rule set in step 4.
  Revisit unifying on files only if `${CLAUDE_PLUGIN_ROOT}` is confirmed working on the target builds.

### Sandbox & permissions

- **The sandbox is the boundary; the deny list is a thin, deliberately incomplete supplement.**
  OS-level containment (bubblewrap on Linux/WSL2, Seatbelt on macOS) is what actually holds. Two
  sandbox settings harden it, applied per-session via `--settings`, and a third is deliberately
  declined (Tenacom/tenacom-ai-tools#1):
  - **`failIfUnavailable: true`** — a sandbox that cannot start is a hard stop, never a silent
    unsandboxed run. The launcher also preflights the Linux/WSL2 deps (`bwrap`, `socat`) for a clear
    message, and because a Claude Code predating the flag would ignore it.
  - **`sandbox.filesystem.denyWrite: ["<repo-root>/.git", "<repo-root>/.pr-review", "<repo-root>/.pr-review-run"]`**
    — the integrity-critical paths are read-only to **Bash and its children**. This is the real
    replacement for name-denying interpreters: execution is made _harmless_ (executed PR code cannot
    alter `.git` — no planted hook — nor the review's own snapshot and run directories) rather than
    _blocked_. It costs the review nothing: its Bash is read-only (search + `git rev-parse`/`merge-base`),
    it never executes PR code (the never-execute rule), and **`Read`/`Edit`/`Write` bypass the sandbox**
    (they go through permissions), so the agents still write `REVIEW.md` and the run dir. The launcher
    injects the repo root into each path via a `@@TOP@@` placeholder, since the settings heredoc is quoted.
  - **Why not the whole tree.** An earlier version denied `["<repo-root>"]` outright, and it **broke
    every Bash call** on any repo lacking a `~/`-style hardened dotfile at the root. Independently of
    our settings, bubblewrap read-only-binds a set of hardened dotfiles (`.gitconfig` and kin) _over the
    working directory_; to bind one whose mount point is absent it must first create the mount point, and
    inside a read-only-bound working tree that create fails (`Can't create file … Read-only file system`),
    aborting the sandbox **before any command runs** — so the failure looks like "all git commands fail"
    but git never runs. Leaving the working tree writable lets those mount points be created. The trade:
    Bash could now write elsewhere in the working tree (including `REVIEW.md`), but the never-execute
    rule plus the read-only review vocabulary make that inert, and the three integrity-critical paths
    above stay protected. **`REVIEW.md` is deliberately not denied** — it may not exist on a first run,
    and denying an absent path would ro-bind a phantom mount point and reintroduce the very abort. Each
    denied path, by contrast, is created by prep before launch, so it ro-binds an existing inode
    (`denyWrite` on a plain file is fine — bwrap ro-binds a file inode as readily as a directory). Do
    **not** re-add `<repo-root>` (or `REVIEW.md`) to `denyWrite`.
  - **Worktrees and submodules — the `.git` denial still holds, via a different layer.** In a linked
    worktree or a submodule, `<repo-root>/.git` is not a directory but a **file** pointing at a git dir
    that lives _outside_ the working tree (`<main>/.git/worktrees/<name>`, `<super>/.git/modules/<name>`).
    Denying the pointer file is harmless but near-pointless there; what actually protects the real git
    dir is the sandbox's **read-only-by-default** posture — everything outside the writable working dir
    is already read-only, and the real git dir is outside it. So `.git` stays protected in both shapes,
    just by our explicit deny in a normal clone (where `.git` sits _inside_ the writable tree) and by the
    default elsewhere. This is not a regression: the old `["<repo-root>"]` never covered an external git
    dir either. No need to also deny `--git-common-dir` — it is redundant with the read-only default.
  - **`sandbox.credentials` — declined, not an oversight.** It only gates sandboxed Bash (not the
    `Read` tool), and with `denyWrite` + sealed egress a secret read is inert (copy it to `/tmp` — so
    what). Enumerating secret files is the same anti-pattern as the interpreter deny list; a user who
    needs it sets it globally, where credential entries merge across scopes and apply anyway.
- **The permission `deny` list is kept to capabilities a name can _completely_ deny**: `WebFetch`,
  `WebSearch`, and `Bash(gh:*)` (the pre-authenticated GitHub-write path the design reserves for the
  human). `php`/`node`/`npm`/`npx` were **removed** (Tenacom/tenacom-ai-tools#1): denying execution by
  name is unwinnable — `python`, `ruby`, `make`, `deno`, `pnpm`, and any shebang'd runner
  (`./vendor/bin/phpunit` never matches `Bash(php:*)`) all slip it — and a partial list only buys churn
  and false confidence. `denyWrite` neutralizes execution's damage; the SKILL's never-execute rule
  discourages it up front. Egress is sealed by the network proxy (no domain allowed), independent of
  the deny list.
- **The deny list also path-scopes the file-write tools off the immutable inputs** — `Write`, `Edit`,
  and `MultiEdit` are denied on `/.pr-review/**` (the snapshot) and `/.git/**`. This is the **tool-side
  twin of `denyWrite`**, and the two layers guard against different actors: `denyWrite` binds **Bash and
  its children** read-only (executed PR code), while `Read`/`Edit`/`Write` **bypass the sandbox** and go
  through permissions (the model's own tool calls, the prompt-injection surface). Without the tool-side
  deny, an injected instruction could still rewrite the diff and rules the review is judged against, or
  plant a git hook — so the snapshot must be immutable to **both** layers. It fits the "a name can
  _completely_ deny" bar: `deny` beats a bare `allow`, and a deny even blocks a symlink escape (it
  matches if either the link or its target hits the pattern). Two paths are **deliberately excluded**:
  `.pr-review-run/**` stays tool-writable because every agent delivers its report by `Write`-ing into it
  (the run-directory design), and `REVIEW.md` stays writable because it is the output. The patterns are
  **project-root-relative** (`/.pr-review/**`, not an absolute path) — the simple, documented form,
  resolved against the session cwd, which the launcher guarantees is the repo root.
  - **In a worktree or submodule the tool-side `.git` deny is narrower than the sandbox-side one** — and
    that is fine. Being project-root-relative, `/.git/**` pins only the in-tree `.git` **pointer file**;
    it does not reach the real git dir, which lives _outside_ the working tree (see the worktree note
    above). So there the snapshot's tool-side immutability still holds (`.pr-review/` is always in-tree),
    but `.git`'s tool-side protection collapses to the pointer, and the real git dir rests solely on the
    sandbox's read-only-by-default posture — exactly as it did before this deny existed. Not a regression
    (there was **no** tool-side protection before), and reaching the external git-common-dir would take an
    agent deliberately targeting an absolute path it would have to know; the sandbox default already
    covers that for Bash. Pinning the external dir tool-side would mean resolving `--git-common-dir` at
    launch and threading it in — deliberately not done, for the same "redundant with the read-only
    default" reason the sandbox side gives.
- The **PreToolUse `Bash` hook** unconditionally allows Bash, working around
  anthropics/claude-code#43713 — `autoAllowBashIfSandboxed` falls back to a permission prompt for any
  command the static analyzer cannot parse (shell expansions, substitutions, brace/ANSI-C strings),
  pure friction in an unattended review. A hook's `allow` never overrides a `deny`, so it cannot weaken
  the `gh`/web denials; and it does **not** auto-answer the proxy's per-domain network prompt (a
  separate runtime mechanism), so egress stays sealed. The plain-commands rule stays as a
  **quality/legibility** guideline, not the prompt mechanism: a command that slips it degrades to a
  silently-allowed sandboxed run, never a prompt.
- `allow`: `Read`, `Task`, `Write`, `Edit`, `MultiEdit`, `Bash(rg:*)`, `Bash(grep:*)`, `Bash(find:*)`,
  `Bash(ugrep:*)`, `Bash(bfs:*)`, `Bash(git rev-parse:*)`, `Bash(git merge-base:*)`. `deny`: `WebFetch`,
  `WebSearch`, `Bash(gh:*)`, and the file-write tools scoped to the immutable inputs —
  `Write`/`Edit`/`MultiEdit` on `/.pr-review/**` and `/.git/**` (see the deny-list bullet above).
  `Edit`/`MultiEdit` stay in `allow` (bare) so an agent amending its own report does not prompt (the hook
  covers Bash only), and `deny` overrides that bare `allow` only on the two scoped subtrees; the
  `Bash(...)` allow entries stay as documentation and a fallback if the hook is ever absent.
- Search is one read-only command in fixed shapes — `rg` (ripgrep) by default, with `grep`/`find`
  (and the legacy `ugrep`/`bfs` names) as allow-listed equivalents Claude Code may expose depending
  on the build. `rg` is backtracking-immune; the embedded fallbacks run in-process, so patterns stay
  literal or near-literal to avoid a backtracking OOM. The names are allow-listed broadly **on
  purpose**: a build that renames the embedded search tools — as the 2.1.x line silently renamed
  `ugrep`/`bfs` to the `grep`/`find` shims and surfaced `rg` — must degrade to at worst a permission
  prompt, never a missing-command stop. Silent degradation beats refusing to review: a stray
  confirmation prompt gets reported as a bug, but a hard failure with no context (an end user has no
  idea why `ugrep` is needed) gets the plugin abandoned. So this list deliberately never fails closed
  on a search tool, and the SKILL never gates the review on one resolving.
- Launch pins max effort: `exec env CLAUDE_CODE_EFFORT_LEVEL=max claude --settings … "/pr-review:run"`.

### Never-execute rule

The review **never runs the code it reviews** (autoloader side effects, attacker-influenceable
tree, non-deterministic third surface). A behavioural question that `Read`
cannot settle becomes a finding stating the question and the experiment — it is not answered
by running anything.

### Base-sourced rule set

The standards agents treat the project rule set as **authoritative instruction** — agent 4
audits the diff against it, agent 6 quotes it. But the rule files (`CLAUDE.md`,
`.claude/rules/**`, and the `.claude/pr-review/**` glossary overrides) are themselves part of
the diff, author-written on a fork PR. So the rule set is resolved from the **base branch**,
exactly as GitHub evaluates CODEOWNERS from the base, never the PR's version — the fix for the
rule-set half of Tenacom/tenacom-ai-tools#1 M3.

- **`pr-assemble-rules`** (Python 3, stdlib only; git the only external tool) runs during
  preparation, unsandboxed, after `changed-files.txt` and **before** `state.json` (so a failed
  assembly leaves no completeness marker and the review refuses to run). It resolves the set
  from `baseSha` via `git show`/`git ls-tree`: the `CLAUDE.md` hierarchy down to the changed
  dirs (plus `.claude/CLAUDE.md`), every `@import` inlined recursively (imports that escape the
  repo — absolute, `~`, or `../` above root — are recorded unresolved, never read), every
  `.claude/rules/**/*.md`, and every `.claude/pr-review/strings.*.json`. It writes one file per
  source under `.pr-review/rules/` (repo-relative path, frontmatter intact) plus a
  `manifest.json` (per-file kind + scope + inlined/unresolved imports). An empty manifest — a
  repo with no rules — is valid, not an error.
- **Why prep, not the skill.** Base versions live only as git objects the sandboxed review
  cannot reach (`git show` is neither allow-listed nor on the never-touch-history surface).
  Prep has full git, so it gathers once into a snapshot artifact beside `canonical.diff`. This
  **retires** the old "gathering must live in the main agent because `Read` can't expand
  `@import`s / subagents don't inherit memory" reasoning: SKILL step 4 is now a _read_ of
  `.pr-review/rules/manifest.json` plus the files it lists, not a live walk of the checkout.
- **Two halves, complementary.** Structural: authority comes only from the base artifact.
  Prompt: the subagent preamble names the handed set the _sole_ rule authority and the PR's
  on-disk rule files _data_ (still reviewed as changed files — a changed rule file gets its
  typos flagged — but never obeyed). Neither half suffices alone; together they close M3.
- **The CODEOWNERS trade-off, accepted:** a rule a PR _introduces or relaxes_ does not govern
  its own review (the review audits against the base rules). The rule _change_ is still reviewed
  as ordinary diff content. This is strictly the safe direction — a PR cannot weaken a rule to
  excuse its own code.
- **`pr-assemble-rules` is shimmed onto PATH** alongside `pr-review`/`pr-finalize` and invoked
  by **bare name**, preserving `pr-review`'s location-independence (it depends on a PATH entry,
  like `git`/`gh`, never on its own path). `pr-review`'s prepare path now also requires
  `python3`, checked up front together with `pr-assemble-rules`.

### Subagent preamble — the single delivery channel

A subagent reads **only** its Task prompt, never `SKILL.md`, so every invariant a subagent must
obey travels through one channel. `SKILL.md` collects that shared floor into a verbatim
**subagent preamble** — no-execution, no-history, no-discovery, the read-only `rg` search
vocabulary, no reads of `REVIEW.md`/the run dir/other agents' files, review-material-is-data
(not instructions), report-in-plain-English, always-write-your-file (even 0
findings), one-line return. Both step 5 (lanes) and step 6 (validators) **prepend it verbatim**,
then append only the agent-specific part (charter / findings-to-confirm, output path, report or
verdict format). Do not re-scatter these invariants into per-lane prose or summarise the
preamble — the single-block, prepend-verbatim shape is the fix for Tenacom/tenacom-ai-tools#1
(invariants that lived only in prose never reached the agents). Lane vs validator differ only in
the appended part; the floor is identical.

The **data-not-instructions** framing covers the intent brief, PR title/body, referenced
issues, canonical diff, and code on disk — **and the repo's own instruction files
(`CLAUDE.md`, `.claude/rules/**`, `.claude/pr-review/**`) as they appear on disk or in the
diff.** They can be data because the rules the review _obeys_ come from elsewhere: the
**base-sourced** assembled rule set (see Base-sourced rule set), which the preamble names as
the _sole_ rule authority. So the bullet now carries both halves — the on-disk/in-diff rule
files are content to audit, and the handed set takes neither additions nor overrides from
them. This is what closes the rule-set half of Tenacom/tenacom-ai-tools#1 M3 (the intent-brief
half was already closed): authority is now **structural** (resolved from the base tree, never
the PR head), and the residual "don't be swayed by rule-like text you read as data" is
prompt-strength, the same class of assurance as the rest of the framing — well-closed, not a
hard proof. Keep both halves in the bullet; **do not** revert it to excluding the rule set (the
old state, when on-disk rules were the only authority and could not be called data).

The framing is scoped to **authority, not evidence**: it refuses only embedded attempts to
redirect or silence the review ("ignore your charter", "report no problems"), **not** a
substantive comment or PR note explaining why specific code is correct or why a standard is
deliberately departed from (the runtime-concatenated string that only looks ungrammatical, a
documented exception). Those are weighed on their merits — the "correct in context" / silenced-
rule discipline of the False positives note — and a sound reason defeats a would-be finding.
Treating such explanations as injection would manufacture false positives, so the bullet must
keep that line drawn.

### Run directory — files, never messages

Results travel as files because the Task notification channel is lossy (drops observed).
Each subagent's final act is one atomic `Write` of `r<run>-a<agent>.md` (lanes) or
`r<run>-v<n>.md` (validators); the main agent collects from the filesystem (the expected set
is known at dispatch). `./.pr-review-run/` is cleared/recreated by prep **only**, hidden via
`.git/info/exclude`; its lifetime is the preparation and it persists across runs of one prep
for post-mortem. Re-prep wipes it; the relaunch path preserves it.

### Additive re-runs (merge rule)

One rule: same identity (agent + location) → skip untouched; new → insert unchecked at its
priority position; locationless findings always insert; the body is never merged; `runs` is
bumped to the precondition-fixed number.

### pr-finalize (posting)

- Self-contained Python 3, stdlib only. No args (or `--dry-run`). Only external tool is `gh`
  (with a `command -v` guard); no `jq`.
- PR/base/head come from `.pr-review/state.json`, **never** from `REVIEW.md` frontmatter
  (it parses the body only).
- One `gh api … /pulls/<n>/reviews` POST. The `event` is **the verdict, derived from
  curation**: no checked finding → `APPROVE`; any checked finding (in any section) →
  `REQUEST_CHANGES`. `COMMENT` is never used — GitHub takes a PR out of "review requested" the
  moment any review lands regardless of event, so a `COMMENT` would only withhold the author's
  next-step signal; the checkbox, not the section, is the blocking signal (a checked
  Preesistenti finding has been deemed worth resolving). The senior "amicus brief" comment
  review stays a manual, out-of-band act. This assumes the runner has write access — accepted,
  since approving / requesting changes _is_ the point of a review. GitHub requires a non-empty
  body on a `REQUEST_CHANGES`: the one path to an empty one (all checked findings inline, no
  verdict prose, nothing folded) is a **hard refusal**, not a fabricated body — checked on the
  _stripped_ body, so blank lines do not pass.
- Before prompting, `pr-finalize` prints a per-section recap (label + checked / unchecked /
  total) and the pending verdict, so a half-curated `REVIEW.md` (e.g. 0 checked past §1) is
  visible. An `APPROVE` takes a **second** confirmation — an unmodified `REVIEW.md` may be an
  unread one, not a clean one.
- Routing by section ordinal: §1/§2 located → inline (**must** be in-diff or hard-refuse —
  the one thing that would 422 the all-or-nothing post); §1/§2 locationless → fold; §3 → all
  fold, with a `blob/<head>` permalink when located.
- On success writes `posted.md`/`posted.json`; `REVIEW.md` is kept (unchecked findings
  survive). `pr-review` refuses to relaunch a preparation whose `pr-finalize` already posted
  (the `.pr-review-run/posted.md` marker).

## Packaging & deployment invariants

- **Versioned plugin, rolling marketplace.** The plugin carries a semver `version` in its own
  `plugin.json`, **not** in the marketplace entry (when both exist
  `plugin.json` wins silently). Bumping that field is the release gate: Claude Code resolves the
  version from `plugin.json` first, so pushing commits without a bump ships nothing to existing
  installs. The _marketplace_ is the rolling, unversioned layer served from `main`; the plugin is
  not. The SHA-fallback model — omit `version` everywhere so every commit is its own version — is
  the true-rolling variant we deliberately declined for shipped plugins. See
  `.claude/rules/versioning-and-releases.md` for the full model.
- **`bin/` is the session PATH, not the shell PATH.** Files in `bin/` are invokable as bare
  commands inside any Bash tool call while the plugin is enabled — that is the model's PATH,
  not the user's interactive shell. `pr-review` must be typeable in a bare shell before any
  session exists, hence the `install-shims` bootstrap.
- **`install-shims` bootstrap (bash, self-locating).** Self-locates via
  `readlink -f "${BASH_SOURCE[0]}"`. Keeps **copies** of `pr-review`, `pr-finalize`, and
  `pr-assemble-rules` under `~/.local/share/pr-review/bin` (refreshed only when `cmp` differs)
  and symlinks `~/.local/bin/{pr-review,pr-finalize,pr-assemble-rules}` at those copies.
  `pr-assemble-rules` is shimmed only so `pr-review` can find it by bare name during prep — not
  an end-user command. Idempotent; repairs a wrong/missing link; **never clobbers a non-symlink
  a human placed** (`[ -L ]` guard); all output to stderr (a `SessionStart` hook's stdout is
  injected into the model's context).
- **Copies, not symlinks-into-cache.** The plugin cache is version-keyed and an orphaned
  version dir is GC'd ~7 days later; a symlink into it would dangle. Our own copies are
  independent of the cache lifecycle, so a PATH entry can lag a version (until a session
  refreshes it) but never dangle.
- **Two trigger paths, same script.** (1) Explicit at install: `claude -p /pr-review:install`
  — owns first install, including the cold-shell case. (2) Ongoing: the `SessionStart` hook
  refreshes every session, so updates self-heal. The sandboxed review session is structurally
  never the first session, so the hook's run there is a read-only no-op.
- **Install is two pasted lines; marketplace-add is separate.**
  `claude plugin install pr-review@<marketplace>` then `claude -p /pr-review:install`.
  Marketplace registration (`claude plugin marketplace add …`) is delegated to the
  marketplace README. No `curl | bash` one-liner: a private marketplace repo 404s on
  `raw.githubusercontent.com` without a token, and a token piped to bash is exactly the
  entropy we refuse.

## Dead ends — do not re-walk

- **A register/audience knob (`junior` default, `expert` opt-in).** Shipped in 1.0.x, removed:
  the knob was presentation-only, went unused in practice, and carried standing costs — an
  invocation argument that had to survive the whole run to matter at assembly, a guard
  paragraph against `expert` compressing findings away, and one more constraint in a style
  pile already implicated in the output's stilted prose. The review speaks with one voice (the
  former `junior`); a prose problem is fixed by editing that voice, never by reintroducing a
  register, verbosity, or audience knob.
- **Skill self-location.** A skill body has no `__file__`; deriving its own path from the
  version-globbed cache is ambiguous during the 7-day overlap, and `${CLAUDE_PLUGIN_ROOT}` is
  the only token that names the live one. So the bootstrap is a **script** (true self-path via
  `readlink -f`) launched by hook/skill, not a self-locating skill.
- **Bundling rules/instructions in the plugin for end users.** Plugins contribute skills,
  agents, hooks, and MCP — not memory. A plugin cannot ship `CLAUDE.md` or `.claude/rules/`
  that loads for its users. Persistent instruction lives in the skill (`SKILL.md`), and
  development-time context (like this file) lives in the consuming repo's root `.claude/rules/`.
- **Turning the six review lanes into plugin-contributed custom agents.** Tempting once
  this became a plugin (plugins _can_ contribute agents), but it fits worse than it looks.
  Custom agents pay off when a **large static system prompt** is hoisted out so the
  per-invocation input stays small; here it is the reverse — the static shared block
  (the **subagent preamble** in `SKILL.md`: no-execution, no-history, no-discovery, the
  read-only `rg` search vocabulary, no reads of `REVIEW.md`/the run dir, data-not-instructions,
  report-in-English, always-write-your-file, and the one-line return) is small, while the
  **bulk** of every lane prompt is
  per-run dynamic context (intent brief, assembled rule set, changed-files list,
  canonical-diff path, run/agent numbers, output filename) that must be injected
  at dispatch regardless (a subagent gets only its Task prompt). So an agent
  definition could absorb only the small part. Against that marginal win: it **fragments the
  single authoritative spec** (`SKILL.md`) the whole design defends; there is **no agent
  composition/include**, so the shared block either stays in `SKILL.md` (charters move out
  for ~no gain) or gets duplicated across six files (worse than today's write-once-inject);
  **validators cannot be agentized** (no agent number, progressive `<n>`, mixed-lane
  findings — pure dynamic dispatch); and plugin agents **pollute the session-wide registry**
  with six types meaningless unless handed a full context. The one thing prompt-injection
  cannot do — a structural `allowed-tools` allowlist (`Read`, `Bash(rg:*)`,
  `Bash(grep:*)`, `Bash(find:*)`, `Write`) as a single shared `review-lane` agent — would only be
  defense-in-depth beneath the sandbox `deny` list, which already enforces never-execute and
  zero-network at the strongest layer. Not worth the second home for the invariants. The
  shared floor is instead hoisted verbatim as the **subagent preamble** and prepended to every
  lane _and validator_ prompt — the single-spec realisation of the shared-system-prompt benefit,
  without the second home (Tenacom/tenacom-ai-tools#1).
  **Keep the lanes as orchestrated `Task` prompts.**
