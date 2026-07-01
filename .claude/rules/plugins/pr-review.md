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
the full local source (not just the diff), with a two-register presentation (`junior`
default, `expert` opt-in). The review runs **sandboxed with zero network, zero prompts,
zero reliance on the Task notification channel**; everything network- or write-side lives
outside the sandbox, in two companion commands — `pr-review` (bash) prepares and launches,
`pr-finalize` (Python) posts. The whole thing is distributed as a Claude Code plugin named
`pr-review`, installed from a private marketplace.

## Canonical names — do not drift

One scheme. Both end-user commands are `pr-<verb>`. The command `pr-review` deliberately
equals the plugin name and the skill namespace stem; these are separate namespaces (a PATH
executable, a plugin id, a skill prefix) so there is no collision, and the entry-point
command sharing the plugin name is a coherence win.

| Thing                      | Canonical name        |
| -------------------------- | --------------------- |
| Prepare/launch command     | `pr-review`           |
| Post command               | `pr-finalize`         |
| Review skill invocation    | `/pr-review:run`      |
| Review skill `name:` / dir | `run` / `skills/run/` |
| Snapshot dir (repo root)   | `.pr-review/`         |
| Run dir (repo root)        | `.pr-review-run/`     |

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
│   └── install-shims            #   PATH bootstrap (bash, self-locating)
├── skills/
│   ├── run/SKILL.md             #   the review — name: run → /pr-review:run; THE SPEC
│   └── install/SKILL.md         #   /pr-review:install — thin trigger for install-shims
├── hooks/hooks.json             #   SessionStart → "${CLAUDE_PLUGIN_ROOT}"/bin/install-shims
└── README.md
```

The three `bin/` files must be committed mode `755` (git tracks the bit; some output mounts
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
  English glossary and flags it as improvised.
- **The posting path is language-agnostic by construction** — `pr-finalize` routes by section
  ordinal and the `^###\s+\[([ xX])\]` checkbox, never by heading text — so glossary changes need
  no code change there. Keep it that way: never make `pr-finalize` or `pr-review` key on any
  natural-language string.
- **Built-in glossaries are embedded in `SKILL.md`, not JSON files in the skill dir** —
  deliberately, against the (tempting) DRY instinct of one file mechanism for built-in and
  pluggable alike. Two reasons: a skill cannot reliably locate its own directory (see Dead ends →
  Skill self-location; `${CLAUDE_PLUGIN_ROOT}` is still on the verify list), and the `en` reference
  is needed **every run** as the fallback anchor, so it must be guaranteed in-context, never behind
  a Read that can fail on a bad plugin root. The override files escape this because their path is
  **repo-root-relative** (`.claude/pr-review/strings.<code>.json`) — reliable, same as the
  `.claude/rules/**` reads in step 4. Revisit unifying on files only if `${CLAUDE_PLUGIN_ROOT}` is
  confirmed working on the target builds.

### Sandbox & permissions

- Zero egress, enforced by the `deny` list (deny wins across scopes — **including over a hook's
  `allow`**). Zero prompts is delivered by a **PreToolUse `Bash` hook** in the sandbox settings
  that unconditionally allows Bash: it works around `autoAllowBashIfSandboxed` being defeated by
  the static analyzer on anything it cannot parse (shell expansions, substitutions, brace/ANSI-C
  strings — Claude Code bug anthropics/claude-code#43713, still open). The hook makes the sandbox
  the boundary, as the setting intends; because a hook's `allow` never overrides `deny`, it cannot
  weaken never-execute/egress — the deny list still blocks `gh`/`php`/`node`/`npm`/`npx`. The
  plain-commands rule stays, but as a **quality/legibility** guideline now, not the prompt
  mechanism: a command that slips it degrades to a silently-allowed sandboxed run, never a prompt.
- `allow`: `Read`, `Task`, `Write`, `Edit`, `MultiEdit`, `Bash(rg:*)`, `Bash(grep:*)`, `Bash(find:*)`,
  `Bash(ugrep:*)`, `Bash(bfs:*)`, `Bash(git rev-parse:*)`, `Bash(git merge-base:*)`. `deny`: `WebFetch`,
  `WebSearch`, `Bash(gh:*)`, `Bash(php:*)`, `Bash(node:*)`, `Bash(npm:*)`, `Bash(npx:*)`. `Edit`/`MultiEdit`
  are allowed so an agent amending its own report does not prompt (the hook covers Bash only); the
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
- Launch pins max effort: `exec env CLAUDE_CODE_EFFORT_LEVEL=max claude --settings … "/pr-review:run [register]"`.

### Never-execute rule

The review **never runs the code it reviews** (autoloader side effects, attacker-influenceable
tree, writable sandbox, non-deterministic third surface). A behavioural question that `Read`
cannot settle becomes a finding stating the question and the experiment — it is not answered
by running anything.

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

- **Rolling release.** `version` is omitted from both `plugin.json` and the marketplace entry
  → Claude Code falls back to the git commit SHA, so every marketplace commit is a new version
  and `/plugin update` always advances. Setting `version` anywhere silently pins it.
- **`bin/` is the session PATH, not the shell PATH.** Files in `bin/` are invokable as bare
  commands inside any Bash tool call while the plugin is enabled — that is the model's PATH,
  not the user's interactive shell. `pr-review` must be typeable in a bare shell before any
  session exists, hence the `install-shims` bootstrap.
- **`install-shims` bootstrap (bash, self-locating).** Self-locates via
  `readlink -f "${BASH_SOURCE[0]}"`. Keeps **copies** of `pr-review` and `pr-finalize` under
  `~/.local/share/pr-review/bin` (refreshed only when `cmp` differs) and symlinks
  `~/.local/bin/{pr-review,pr-finalize}` at those copies. Idempotent; repairs a wrong/missing
  link; **never clobbers a non-symlink a human placed** (`[ -L ]` guard); all output to
  stderr (a `SessionStart` hook's stdout is injected into the model's context).
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

## Still to verify

These live paths were unconfirmed when the plugin was packaged; confirm before trusting them.

- **Carried**: dead-lane relaunch drill; deny rules fail fast (no prompt) for
  `gh`/`php`/`node`/`npm`/`npx` from a subagent; VS Code `###`-click lands right with the
  literal `[ ]` heading; Precondition-5 hard gate; behavioural-question-as-finding.

## Dead ends — do not re-walk

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
  (agent assumptions, never-execute, the closed read-only search vocabulary, the run-directory
  write protocol, the return format) is small, while the **bulk** of every lane prompt is
  per-run dynamic context (intent brief, fully-assembled rule set, changed-files list,
  canonical-diff path, run/agent numbers, output filename) that step 4 requires be injected
  at dispatch regardless (subagents do not reliably inherit loaded memory). So an agent
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
  zero-network at the strongest layer. Not worth the second home for the invariants.
  **Keep the lanes as orchestrated `Task` prompts.**
