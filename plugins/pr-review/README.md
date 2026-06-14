# `pr-review` — sandboxed PR review for Claude Code

An AI-assisted PR-review pipeline, built on Claude Code and shipped as a plugin.

A six-agent parallel review reads the PR against the **full local source** — not just the diff — and writes its findings to a structured `REVIEW.md`. You curate that file by hand, then post the result to GitHub as a single review object.

The review itself runs **sandboxed, with zero network and zero prompts**: everything it needs from GitHub is captured up front into a snapshot, so the part that reads attacker-influenceable text (fork PRs included) can touch nothing.

The plugin ships four moving parts:

- **`pr-review`** — a terminal command (self-contained bash). Prepares the PR branch (fetch, snapshot, recreate base, `gh pr checkout`, rebase, confirmed force-push) and launches the sandboxed review session. Run from a repository root.
- **the `run` skill** — the review itself: the prompt, the six lanes, the validation pass, and the exact `REVIEW.md` grammar. Invoked as `/pr-review:run`, inside the sandbox. **This skill's `SKILL.md` is the spec** for everything about `REVIEW.md`'s format; this README is only an overview.
- **`pr-finalize`** — a terminal command (self-contained Python 3). Posts the curated `REVIEW.md` to GitHub as one review object. Run from a repository root.
- **`install`** — a one-time setup step (`/pr-review:install`) that puts the two commands on your PATH. See _Installation_.

The two commands share no code. They meet at a file contract: the preparation snapshot under `.pr-review/`, plus a `posted.md` marker under `.pr-review-run/` once a review is posted.

## At a glance

Once installed (see _Installation_), a review is three steps, all from a repository root:

```bash
pr-review 142     # prepare the PR and run the sandboxed review → writes REVIEW.md
                  # …then curate REVIEW.md by hand: tick the findings worth posting…
pr-finalize       # post the curated review to GitHub
```

The rest of this README explains each step; _How a review goes_ has the detail.

## Requirements

- **git** and the **GitHub CLI (`gh`)**, authenticated (`gh auth login`) with a default repo set (`gh repo set-default`, pointed at the upstream). Needed by `pr-review`'s preparation and by `pr-finalize`.
- **`claude`** (Claude Code CLI) on `PATH`. Needed to launch the review and to install the plugin.
- **`python3`** — standard on our Ubuntu/WSL targets. Needed by `pr-finalize`, which builds the API payload with the standard library (no `jq` dependency).
- **`bash`** to run `pr-review` and the setup step — both are portable bash; no runtime beyond the tools above.
- **`~/.local/bin` on your `PATH`** — the setup step installs the two commands there. Debian/Ubuntu add this directory to `PATH` automatically (via the default `~/.profile`, once it exists); other distros vary, and minimal setups may need it added by hand. The `command -v` check under _Installation_ is the real test.

## Installation

This plugin lives in the **`tenacom-ai-tools`** marketplace — the [Tenacom/tenacom-ai-tools](https://github.com/Tenacom/tenacom-ai-tools) repository. In a terminal, register the marketplace, install the plugin, then put its commands on your PATH:

```bash
claude plugin marketplace add Tenacom/tenacom-ai-tools
claude plugin install pr-review@tenacom-ai-tools
claude -p /pr-review:install
```

The first line registers this repository as a Claude Code plugin marketplace — a one-time step per machine. The second installs the plugin and its skills. The third puts the `pr-review` and `pr-finalize` commands on your PATH: it creates two symlinks in `~/.local/bin`, backed by copies it keeps under `~/.local/share/pr-review/bin`. A `SessionStart` hook re-runs the same step on later sessions, so the commands stay current after a plugin update — you only run the third line once.

Make sure `~/.local/bin` is on your `PATH`. Debian/Ubuntu add it via the default `~/.profile` once the directory exists — but only in a **new login shell**, so start one after the first install; other distros may need it added by hand. Verify:

```bash
command -v pr-review pr-finalize
```

## How a review goes

1. **Prepare and review.** From a repository root, in a terminal:

   ```bash
   pr-review 142            # default "junior" register
   pr-review 142 expert     # "expert" register
   ```

   The _register_ sets the review's tone: `junior` (the default) explains more, `expert` is more concise.

   This prepares `pr/142`: it checks out the branch, rebases it, and — only if the rebase rewrote the branch — asks at the terminal before force-pushing, so the PR head on GitHub matches what you review. It then captures the GitHub snapshot into `./.pr-review/` and launches an interactive sandboxed `claude` session running `/pr-review:run`. The review reads the snapshot and the checkout, runs its six lanes plus a validation pass, and writes `REVIEW.md` at the repo root. It makes no network calls.

   To prepare without reviewing — to inspect the tree first — use `pr-review prepare 142`, then review later with `pr-review 142` or, from an already-open session on the prepared branch, `/pr-review:run`.

2. **Curate `REVIEW.md`.** The file's body is the PR-level comment; each `###` block is one finding, with an unchecked `[ ]` checkbox. **Nothing posts until you check it.** Tick the findings worth posting (`[x]`), edit prose or section labels as you like, and leave the rest unchecked — unchecked findings stay in the file as a record and post nothing.

3. **Preview, then post.** From the repository root:

   ```bash
   pr-finalize --dry-run    # parse, route, print the exact payload — posts nothing
   pr-finalize              # post the review, after a recap and a terminal confirmation
   ```

   Checked findings under Problems or Observations that sit on changed lines post as inline comments. Everything else is _folded_ — merged into the PR-level body under its section label. The verdict follows from your curation: with **no** checked finding it posts an **approval**; with **any** checked finding — in any section — it **requests changes** (the checkbox, not the section, decides). Before prompting, `pr-finalize` prints a per-section recap (checked / unchecked / total), so a half-read `REVIEW.md` is visible, and an approval takes a second confirmation. On success it leaves a `posted.md` marker that closes the preparation.

### Re-runs and re-preparation

Within one preparation, re-running the review **stacks onto** `REVIEW.md` rather than overwriting it: findings already present are left untouched (checked or not, however you moved or edited them), and new ones are inserted **unchecked**. Because only checked blocks post, anything the merge gets wrong has no effect until you approve it.

A finalized preparation is closed: a second `pr-finalize` refuses, and so does a re-review. To start over against the current head, **re-prepare** — delete `REVIEW.md` and run `pr-review 142` again. Re-preparation wipes the snapshot, the run directory, and the marker.

### Why the split

Preparation needs the network and writes to `.git/config`, so it runs **unsandboxed**. The review needs neither, reads untrusted text, and so runs **sandboxed with zero egress** — its entire GitHub context is the snapshot taken before the sandbox closed. Posting needs the network again, so `pr-finalize` runs **unsandboxed** too. `pr-review` is the boundary between the first two; the file contract is the boundary between the review and `pr-finalize`.

All review artifacts — `.pr-review/`, `.pr-review-run/`, and `REVIEW.md` — are hidden from `git status` through `.git/info/exclude` (maintained by the preparation), never `.gitignore`. They never enter the project's history and never make the next preparation see a dirty tree.

## Language support

The review is written **in the natural language of the PR** — title and body — so the author reads it in the language they wrote in. Most of `REVIEW.md` is free prose the model writes directly; a small set of structural labels (the three section headings, the `Status:` line, and the status table's outcomes and headers) comes from a fixed **glossary** so they stay stable across runs and curation.

**English, Italian, and Spanish** are built in. To support another language, drop a glossary file at `.claude/pr-review/strings.<code>.json` in the repo being reviewed (`<code>` is the language's ISO 639-1 code, e.g. `fr` for French, `de` for German). Copy the reference shape below — the English values, which are also the built-in `en` glossary — and translate each value into your language:

```json
{
  "sections": { "problems": "Problems", "observations": "Observations", "preexisting": "Pre-existing" },
  "status": {
    "heading": "Status:",
    "outcomes": { "ok": "OK", "partial": "Partial", "missing": "Missing" },
    "columns": { "requirement": "Requirement / Declared change", "outcome": "Outcome", "note": "Note" }
  }
}
```

A file present for a built-in language overrides the built-in, so you can tune terminology. With no glossary for the PR's language, the review still runs — it makes up the labels and warns you, so you can fix them with a `strings.<code>.json`. (Deeper prose conventions — grammatical gender, terminology, tone — belong in the repo's `.claude/rules/`, like any other project convention; the glossary covers only the structural labels.)

## Updating and uninstalling

- **Update the plugin:** `claude plugin update pr-review@tenacom-ai-tools`. This is a rolling release (no pinned version), so a new commit to the marketplace is a new version; the next session's hook refreshes the on-PATH copies automatically. If you have not opened a session in a while, run `claude -p /pr-review:install` again to force the refresh.
- **Uninstall:** `claude plugin uninstall pr-review@tenacom-ai-tools`, then remove the PATH entries and the copies the setup step created:

  ```bash
  rm -f ~/.local/bin/pr-review ~/.local/bin/pr-finalize
  rm -rf ~/.local/share/pr-review
  ```

  (The plugin's own files are removed by `claude plugin uninstall`; only the on-PATH shims and their backing copies live outside the plugin and need this manual cleanup.)

## Reference

- **The `run` skill's `SKILL.md` is the spec** for the review and for the `REVIEW.md` grammar — the three lexical rules, the `###` heading shape, the checkbox-as-curation primitive, the three sections, the anchor lint, the two registers, and the worked example. This README does not restate it.
- **`pr-review <id> [register]`** prepares and reviews; **`pr-review prepare <id>`** prepares only; **`/pr-review:run [register]`** runs the review in an already-prepared session.
- **`pr-finalize`** posts; **`pr-finalize --dry-run`** previews the payload and posts nothing.
- **`/pr-review:install`** puts the two commands on your PATH (run once, at install).
