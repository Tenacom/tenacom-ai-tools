# `pr-review` — AI-drafted, human-curated review for GitHub PRs

An AI-assisted PR-review pipeline for GitHub repositories, built on Claude Code and shipped as a plugin.

Human review is thorough but slow; AI review is fast but flawed. `pr-review` does not try to automate review away — it splits the work where each side is strongest. The AI does the heavy lifting: reading, cross-checking, drafting findings into a structured `REVIEW.md`. You make every call that matters: nothing reaches GitHub until you tick it. Each known weakness of AI review gets a structural answer, not a promise:

| _AI review tends to…_                 | _`pr-review` answers with…_                                                                  |
| ------------------------------------- | -------------------------------------------------------------------------------------------- |
| miss findings on a single pass        | idempotent re-runs: new findings stack into `REVIEW.md`, duplicates merge, curation survives |
| judge the diff out of context         | a review run inside the repository, against the full checkout                                |
| hallucinate problems                  | human curation as the core primitive: unchecked findings post nothing                        |
| write odd, needlessly technical prose | fixed wording instructions and one plain-spoken voice that explains concepts in place        |

One more property matters when the PR comes from a stranger: the part that reads attacker-influenceable text runs sandboxed, with zero network access and zero prompts — its entire GitHub context is a snapshot taken beforehand.

---

- [The short version](#the-short-version)
- [Requirements](#requirements)
- [Installation](#installation)
- [Reviewing a PR](#reviewing-a-pr)
  - [Prepare and review](#prepare-and-review)
  - [Curate `REVIEW.md`](#curate-reviewmd)
  - [Preview, then post](#preview-then-post)
  - [Your own findings: draft them as a pending review](#your-own-findings-draft-them-as-a-pending-review)
  - [Re-runs and re-preparation](#re-runs-and-re-preparation)
- [How it works](#how-it-works)
  - [The moving parts](#the-moving-parts)
  - [Why the split](#why-the-split)
  - [Artifacts](#artifacts)
- [Keeping dependencies in sync](#keeping-dependencies-in-sync)
- [Language support](#language-support)
- [Updating and uninstalling](#updating-and-uninstalling)
- [Reference](#reference)

---

## The short version

Once [installed](#installation), a review is three steps, all from a repository root:

```bash
pr-review 142     # prepare the PR and run the sandboxed review → writes REVIEW.md
                  # …then curate REVIEW.md by hand:
                  #   - tick the findings worth posting
                  #   - adjust wording if desired
pr-finalize       # post the curated review to GitHub
```

[Reviewing a PR](#reviewing-a-pr) explains each step in detail.

---

## Requirements

- **Linux**, native or under WSL2, with **`bwrap`** (bubblewrap) and **`socat`** available for the sandbox. `pr-review` checks for both up front.
- **git** and the **GitHub CLI (`gh`)**, authenticated (`gh auth login`) with a default repo set (`gh repo set-default`, pointed at the upstream).
- **Claude Code CLI** (`claude`) on `PATH`.
- **`python3`**, standard on most popular distros. Used during preparation to assemble the rule set, and by `pr-finalize` to build the API payload.
- **`bash`**. Both `pr-review` and the setup step are portable bash, with no runtime beyond the tools above.
- **`~/.local/bin` on your `PATH`**. The setup step installs the commands there. Debian and Ubuntu add this directory to `PATH` automatically (via the default `~/.profile`, once the directory exists); other distros vary, and minimal setups may need it added by hand. The `command -v` check under [Installation](#installation) is the real test.

---

## Installation

This plugin lives in the **`tenacom-ai-tools`** marketplace — the [Tenacom/tenacom-ai-tools](https://github.com/Tenacom/tenacom-ai-tools) repository. In a terminal, register the marketplace, install the plugin, then put its commands on your `PATH`:

```bash
claude plugin marketplace add Tenacom/tenacom-ai-tools
claude plugin install pr-review@tenacom-ai-tools
claude -p /pr-review:install
```

- The first line registers the repository as a Claude Code plugin marketplace; it is a one-time step per machine.
- The second line installs the plugin and its skills.
- The third line is a required post-installation step: it creates symlinks in `~/.local/bin` for `pr-review`, `pr-finalize`, and the internal `pr-assemble-rules` helper, backed by copies kept under `~/.local/share/pr-review/bin`. A `SessionStart` hook re-runs the same step on later sessions, so the commands stay current after a plugin update; you only run the third line once.

> [!TIP]
>
> If you get billed separately for headless Claude Code usage, running the post-installation step in an interactive session is a more budget-savvy choice.
>
> - Type `claude /pr-review:install` (without `-p`) in your terminal to execute the command in an interactive Claude Code session.
> - When the command is done, exit the CLI with `/exit`.

Make sure `~/.local/bin` is on your `PATH`. Debian and Ubuntu add it via the default `~/.profile` once the directory exists, but only in a **new login shell**, so you need to log out and back in if `~/.local/bin` did not exist prior to installation (or run `source ~/.profile` to fix the current shell without logging out).

To verify whether the plugin's commands are accessible, type the following in your terminal:

```bash
command -v pr-review pr-finalize
```

---

## Reviewing a PR

### Prepare and review

From a repository root, in a terminal:

```bash
pr-review 142
```

This prepares `pr/142`: it checks out the branch, rebases it, and, only if the rebase rewrote the branch, asks at the terminal before force-pushing, so the PR head on GitHub matches what you review. It then captures the GitHub snapshot into `./.pr-review/` and launches an interactive sandboxed `claude` session running `/pr-review:run`. The review reads the snapshot and the checkout, runs its six lanes plus a validation pass, and writes `REVIEW.md` at the repo root. It makes no network calls.

To prepare without reviewing, say to inspect the tree first, use `pr-review prepare 142`; then review later with `pr-review 142` or, from an already-open session on the prepared branch, `/pr-review:run`.

### Curate `REVIEW.md`

The review's whole output is one Markdown file, `REVIEW.md`, at the repository root. It is a draft, not a verdict: **nothing in it reaches GitHub until you approve it, finding by finding**. You curate by editing the file in place, with any editor. Trimmed to the bone, a fresh `REVIEW.md` looks like this:

```markdown
| Requirement / Declared change | Outcome |
| --- | --- |
| Detail page on its own route | ⚠️ Partial |

## Problems

### [ ] 1 1 [app-routing.module.ts L34](./src/app/app-routing.module.ts#34)

The route becomes `user-cms/:id`, so the id now travels in the path — but the
component still reads it from the query string, so `id` stays `0` and the
"missing id" guard fires.

Read the path param with `paramMap.get('id')`.

## Observations

### [ ] 1 5

The PR says "Fixes #839", but the detail page still depends on the service
that issue wants gone. Unless you're already close on that work, I'd drop the
"Fixes" and open a follow-up — this PR is coherent as a route move. Bring it
in here, or split it out?

## Pre-existing
```

Three layers:

- **The body** — everything above the first heading — is the future PR-level review comment: a status table matching what the PR declares against what the diff delivers, and nothing else (when the review could not cover part of the change, one sentence saying so precedes the table). The _why_ behind a ⚠️ or ❌ is not in the table: it lives in the finding that backs it, which posts only if you check it.
- **The three `##` sections** — Problems, Observations, Pre-existing, written in the PR's language — classify the findings. All three are always present, even when empty (Pre-existing is, above).
- **Each `###` block is one finding**: the heading carries its metadata, and the prose below it is the comment that would post.

The `###` headings follow a fixed format. Reading the first one above, left to right:

```text
### [ ] 1 1 [app-routing.module.ts L34](./src/app/app-routing.module.ts#34)
     │  │ │ └─ location: file basename + line range, linking to the code
     │  │ └─── agent number: which of the six review lanes found it
     │  └───── run number: which review run produced it
     └──────── the checkbox: your approval, and the only thing that posts
```

The run and agent numbers are provenance — together with the location they identify the finding across re-runs; you never edit them. The location link opens the offending line straight from your editor. It is present only when the finding points at a specific place in the code: a cross-cutting finding — like the "Fixes #839" question above — has no single line to point at, so its heading simply ends at the agent number, and when checked it posts into the PR-level comment instead of inline.

Curation itself is a handful of gestures:

- **Tick what should post.** Turn `[ ]` into `[x]` on each finding worth sending. This is the only action required: the review always delivers every checkbox unchecked, and checking is exclusively your act.
- **Leave the rest unchecked — don't delete.** An unchecked finding posts nothing, ever, and it stays in the file as a record: on a re-run, findings already present are left untouched, so a rejected finding does not come back to be re-litigated.
- **Edit freely below the headings.** The table and each finding's prose are yours to reword, shorten, or fix. You can also reorder findings within a section (order is the only priority signal) and relabel a `##` heading — its text is used verbatim as the group label when its checked findings fold into the PR-level comment.
- **Leave the structure alone.** Don't delete a `##` heading, even over an empty section — sections are identified by position, so removing one would misroute everything below it. And don't rework a `###` heading's checkbox, numbers, or link: that line is the grammar `pr-finalize` parses.

The full grammar, with a complete worked example, lives in the `run` skill's [`SKILL.md`](skills/run/SKILL.md); how checked findings turn into an actual GitHub review is the next step.

### Preview, then post

From the repository root:

```bash
pr-finalize --dry-run    # parse, route, print the exact payload — posts nothing
pr-finalize              # post the review, after a recap and a terminal confirmation
```

Checked findings under Problems or Observations that sit on changed lines post as inline comments. Everything else is _folded_: merged into the PR-level body under its section label. The verdict follows from your curation: with **no** checked finding it posts an **approval**; with **any** checked finding, in any section, it **requests changes**. The checkbox, not the section, decides. Before prompting, `pr-finalize` prints a per-section recap (checked / unchecked / total), so a half-read `REVIEW.md` is visible; an approval takes a second confirmation. On success it leaves a `posted.md` marker that closes the preparation.

### Your own findings: draft them as a pending review

While the review runs — or while curating — you will often spot things yourself, browsing the PR on github.com. Record them with GitHub's own **Start a review** flow: pending comments are saved server-side immediately, anchored to file and line by the UI, and survive a browser restart. Just don't submit the review — `pr-finalize` picks it up.

A pending review would normally block posting (GitHub allows one pending review per user per PR), so `pr-finalize` detects yours and offers to fold it into the single review object it posts: your pending comments join the posted review exactly as you wrote them, your draft summary text (if any) is appended to the end of the review body, and the pending review is deleted from GitHub in the same step. The recap shows what is about to be imported, and everything fetched is first saved verbatim to `.pr-review-run/pending-import.json` as a recovery copy. An imported comment counts as a finding: the posted review requests changes even if no checkbox is ticked.

Declining the import aborts the post — there is no posting around a pending review; to post without importing it, submit or discard it on github.com first, then re-run. Two things cannot ride along in a single review object and are refused by name: replies to existing threads and file-level comments. Handle those in the GitHub UI. `pr-finalize --dry-run` shows the would-be import and touches nothing on GitHub.

### Re-runs and re-preparation

Within one preparation, re-running the review **stacks onto** `REVIEW.md` rather than overwriting it: findings already present are left untouched (checked or not, however you moved or edited them), and new ones are inserted **unchecked**. Because only checked blocks post, anything the merge gets wrong has no effect until you approve it.

A finalized preparation is closed: a second `pr-finalize` refuses, and so does a re-review. To start over against the current head, **re-prepare**: delete `REVIEW.md` and run `pr-review 142` again. Re-preparation wipes the snapshot, the run directory, and the marker.

---

## How it works

### The moving parts

The commands you run yourself, from a repository root:

- **`pr-review`**, a terminal command (self-contained bash). Prepares the PR branch (fetch, snapshot, recreate base, `gh pr checkout`, rebase, confirmed force-push) and launches the sandboxed review session.
- **`pr-finalize`**, a terminal command (self-contained Python 3). Posts the curated `REVIEW.md` to GitHub as one review object.
- **`install`**, a one-time setup step (`/pr-review:install`) that puts the two commands on your `PATH`. See [Installation](#installation).

And the parts `pr-review` drives for you, not meant to be invoked directly:

- **The `run` skill**: the review itself — the prompt, the six lanes, the validation pass, and the exact `REVIEW.md` grammar. Invoked as `/pr-review:run` inside the sandbox, normally launched by `pr-review`; you'd run it by hand only in an already-prepared session. Its `SKILL.md` is the spec for everything about `REVIEW.md`'s format; this README is only an overview.
- **`pr-assemble-rules`**, a self-contained Python 3 helper that `pr-review` runs during preparation. It sources the project's rule set from the PR's **base** branch into the snapshot, so the review judges against rules the PR cannot have rewritten. It shares the `PATH` shim (so `pr-review` can find it by bare name) but is never invoked by hand.

The two commands share no code. They meet at a file contract: the preparation snapshot under `.pr-review/`, plus a `posted.md` marker under `.pr-review-run/` once a review is posted.

### Why the split

Preparation needs the network and writes to `.git/config`, so it runs **unsandboxed**. The review needs neither, reads untrusted text, and so runs **sandboxed with zero egress**; its entire GitHub context is the snapshot taken before the sandbox closed. Posting needs the network again, so `pr-finalize` runs **unsandboxed** too. `pr-review` is the boundary between the first two; the file contract is the boundary between the review and `pr-finalize`.

### Artifacts

All review artifacts (`.pr-review/`, `.pr-review-run/`, and `REVIEW.md`) are hidden from `git status` through `.git/info/exclude`, maintained by the preparation, never through `.gitignore`. They never enter the project's history and never make the next preparation see a dirty tree.

---

## Keeping dependencies in sync

The review never runs the code it reviews, but its agents do **read** your installed dependencies, to resolve the APIs the PR calls against. That reading is only as good as the tree: `node_modules/` or `vendor/` is still synced to whatever you had checked out _before_ you started, not to what the PR declares. A PR that bumps a library reads against the old one — wrong signatures, invented findings, real ones missed.

`pr-review` cannot fix this on its own: which package manager, which flags, which lock file is knowledge only your repository has. So it offers a hook. Commit a shell script at **`.claude/pr-review/sync-deps.sh`** in the repository being reviewed, and the preparation runs it — with `bash`, from the repository root, so it needs no execute bit — after the PR branch is checked out and rebased, and before the review starts. No script, no behaviour: the feature is entirely opt-in, and nothing is auto-detected in its absence.

```bash
# .claude/pr-review/sync-deps.sh
npm ci --ignore-scripts
```

The script's only job is to install dependencies. The preparation checks that this is all it did, and **fails the review** if the script exits nonzero, moves `HEAD`, switches branch, or leaves the working tree dirty — a failed sync produces no reviewable state at all, rather than a review of a tree nobody can vouch for. The mess a misbehaving script leaves is _not_ cleaned up: it is evidence, and `git status` is how you inspect it. The script's output goes to your terminal, so you can see the install happen (and see it go wrong even if the script forgets to fail).

Two details worth knowing:

- **The script is read from the PR's base branch, never from the PR.** Same rule as the project rules the review judges against — a pull request cannot rewrite it. If a PR touches the script, preparation says so and runs the base version anyway. To test a change to your own hook, merge it to the base branch first.
- **`git status` must be clean afterwards**, so the installed dependencies have to land somewhere `.gitignore`d — as they normally do. This is also why the flags matter: `npm ci` respects the lock file, `npm install` rewrites it when it has drifted, which dirties the tree and fails the preparation. Prefer `npm ci` over `npm install`, and `composer install` over `composer update`.

> [!WARNING]
>
> **This hook is a deliberate hole in the plugin's security posture, and you are the one opening it.**
>
> Everything else about the preparation is inert: it fetches, checks out, and reads. This script does not merely run — it runs an **installer**, against **manifests the pull request controls**, unsandboxed and with network access, on your machine. A malicious PR that adds an install-time lifecycle script to `package.json`, or that adds a dependency on a poisoned package, gets that code executed as you, outside the sandbox. No amount of care in `sync-deps.sh` changes this, because the danger is in what the PR feeds it.
>
> That is the trade you accept by committing the file, and it is why the plugin ships no such script and never guesses one. Where your toolchain tolerates them, prefer the flags that shut the door:
>
> - **`npm ci --ignore-scripts`** — `ci`, never `install` (which also rewrites a drifted lock file and would fail the preparation anyway).
> - **`composer install --no-scripts --no-plugins`** — `install`, never `update`.
>
> If you review PRs from people you do not trust and your toolchain cannot install without executing their code, do not use this hook.

**After the review, your own branch has the opposite problem:** the dependencies now match the PR you just reviewed, not the branch you go back to. Reinstall them before you resume work — with your project's ordinary install command (`npm ci`, `composer install`, whatever you normally run), **not** by re-running `sync-deps.sh`.

The distinction matters. A well-written `sync-deps.sh` installs _defensively_, with the lifecycle scripts and plugins turned off, because it is aimed at a stranger's manifests. That is the right call for a review and the wrong one for your own tree: development needs those scripts and plugins to have run. Re-running the hook would leave you with dependencies that look installed and quietly misbehave.

---

## Language support

The review is written **in the natural language of the PR** (its title and body), so the author reads it in the language they wrote in. Most of `REVIEW.md` is free prose the model writes directly; a small set of structural labels (the three section headings and the status table's outcomes and headers) comes from a fixed **glossary**, so they stay stable across runs and curation.

**English, Italian, and Spanish** are built in. To support another language, drop a glossary file at `.claude/pr-review/strings.<code>.json` in the repo being reviewed, where `<code>` is the language's ISO 639-1 code, e.g. `fr` for French. Copy the reference shape below (the English values, which are also the built-in `en` glossary) and translate each value into your language:

```json
{
  "sections": { "problems": "Problems", "observations": "Observations", "preexisting": "Pre-existing" },
  "status": {
    "outcomes": { "ok": "OK", "partial": "Partial", "missing": "Missing" },
    "columns": { "requirement": "Requirement / Declared change", "outcome": "Outcome" }
  }
}
```

A file present for a built-in language overrides the built-in, so you can tune terminology. With no glossary for the PR's language, the review still runs: it makes up the labels and warns you, so you can fix them with a `strings.<code>.json`. Deeper prose conventions (grammatical gender, terminology, tone) belong in the repo's `.claude/rules/`, like any other project convention; the glossary covers only the structural labels.

---

## Updating and uninstalling

- **Update the plugin:** `claude plugin update pr-review@tenacom-ai-tools` picks up the latest released version. The next session's `SessionStart` hook refreshes the on-`PATH` copies automatically; if you have not opened a session in a while, run `claude -p /pr-review:install` again to force the refresh.
- **Uninstall:** `claude plugin uninstall pr-review@tenacom-ai-tools`, then remove the `PATH` entries and the copies the setup step created:

  ```bash
  rm -f ~/.local/bin/pr-review ~/.local/bin/pr-finalize ~/.local/bin/pr-assemble-rules
  rm -rf ~/.local/share/pr-review
  ```

  The plugin's own files are removed by `claude plugin uninstall`; only the on-`PATH` shims and their backing copies live outside the plugin and need this manual cleanup.

---

## Reference

- **`pr-review <id>`** prepares and reviews; **`pr-review prepare <id>`** prepares only; **`/pr-review:run`** runs the review in an already-prepared session.
- **`pr-finalize`** posts; **`pr-finalize --dry-run`** previews the payload and posts nothing. A pending GitHub review of yours on the PR is folded into the post (and deleted), after confirmation.
- **`/pr-review:install`** puts the two commands on your `PATH` (run once, at install).
- **The `run` skill's `SKILL.md` is the spec** for the review and for the `REVIEW.md` grammar: the three lexical rules, the `###` heading shape, the checkbox-as-curation primitive, the three sections, the anchor lint, the voice, and the worked example. This README does not restate it.
