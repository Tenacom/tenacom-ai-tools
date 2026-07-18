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
  - [Check as you curate](#check-as-you-curate)
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
- The third line is a required post-installation step: it creates symlinks in `~/.local/bin` for `pr-review`, `pr-finalize`, `pr-check`, `pr-cleanup`, and the internal `pr-assemble-rules` helper, backed by copies kept under `~/.local/share/pr-review/bin`. Those copies are independent of the plugin cache, so they do not refresh on their own — run this line again after each plugin update (see [Updating and uninstalling](#updating-and-uninstalling)).

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

Just before the review session starts, `pr-review` waits for you to press Enter. The session takes over the terminal, so this is your chance to read what preparation did; press Ctrl-C instead of Enter to stop there and leave the prepared branch checked out.

To prepare without reviewing, say to inspect the tree first, use `pr-review prepare 142`; then review later with `pr-review 142` or, from an already-open session on the prepared branch, `/pr-review:run`.

### Curate `REVIEW.md`

The review's whole output is one Markdown file, `REVIEW.md`, at the repository root. It is a draft, not a verdict: **nothing in it reaches GitHub until you approve it, finding by finding**. You curate by editing the file in place, with any editor. Trimmed to the bone, a fresh `REVIEW.md` looks like this:

```markdown
| Requirement / Declared change | Outcome |
| --- | --- |
| Detail page on its own route | ⚠️ Partial |

## Problems

### [ ] 1 1 [app-routing.module.ts L34](./src/app/app-routing.module.ts#34)

The route becomes `user-cms/:id`, so the id now travels in the path — but the component still reads it from the query string, so `id` stays `0` and the "missing id" guard fires.

Read the path param with `paramMap.get('id')`.

### [ ] 1 2 [task-list.component.ts L49-L55](./src/components/task-list.component.ts#49)

This loop is exactly the same as the one in `_updateData` at [task-list.component.ts L102-L108](./src/components/task-list.component.ts#102) — only two variable names differ.

Extract the loop into a private method and use it at both sites.

## Observations

### [ ] 1 5

The PR says "Fixes #839", but the detail page still depends on the service that issue wants gone. Unless you're already close on that work, I'd drop the "Fixes" and open a follow-up — this PR is coherent as a route move. Bring it in here, or split it out?

## Pre-existing
```

> [!TIP]
>
> **Code links** in `REVIEW.md` always have the format shown in the example above. You can also add your own code links: `pr-finalize` will turn them all into permalinks to the PR's HEAD.
>
> - Links to single lines must be in the form `./path/to/file#<line>`; link text (in square brackets) can be anything.
> - Links to line ranges must be in the form `./path/to/file#<start>` and have a `-L<end>` suffix in the link text.
> - Links to whole files, in the form `./path/to/file` with no `#<line>` at all, are allowed **in prose** — in a finding's text or in the body, not in a `###` heading, whose link is the line the comment posts at.
> - Anything else after the `#` — `#L52`, a section anchor — is an error: `pr-finalize` refuses to post and names the link to fix.
>
> When `REVIEW.md` has more than one problem — a bad link, a finding in the wrong place, an out-of-diff anchor — `pr-finalize` reports them all together, each as a `REVIEW.md:line:column` line you can Ctrl-click in the Visual Studio Code terminal, so you fix them in one pass rather than one re-run at a time.

Three layers:

- **The body** — everything above the first heading — is the future PR-level review comment: a status table matching what the PR declares against what the diff delivers, and nothing else (when the review could not cover part of the change, one sentence saying so precedes the table). The _why_ behind a ⚠️ or ❌ is not in the table: it lives in the finding that backs it, which posts only if you check it.
- **The three `##` sections** — Problems, Observations, Pre-existing, written in the PR's language — classify the findings. All three are always present, even when empty (Pre-existing is, above).
- **Each `###` block is one finding**: the heading carries its metadata, and the prose below it is the comment that would post.

The `###` headings follow a fixed format. Reading the first one above, left to right:

```text
### [ ] 1 1 [app-routing.module.ts L34](./src/app/app-routing.module.ts#34)
     │  │ │ └─ location: a code link — file basename + line range as its text
     │  │ └─── agent number: which of the six review lanes found it
     │  └───── run number: which review run produced it
     └──────── the checkbox: your approval, and the only thing that posts
```

The run and agent numbers are provenance — together with the location they identify the finding across re-runs; you never edit them. The location is present only when the finding points at a specific place in the code: a cross-cutting finding — like the "Fixes #839" question above — has no single line to point at, so its heading simply ends at the agent number, and when checked it posts into the PR-level comment instead of inline.

Curation itself is a handful of gestures:

- **Tick what should post.** Turn `[ ]` into `[x]` on each finding worth sending. This is the only action required: the review always delivers every checkbox unchecked, and checking is exclusively your act.
- **Leave the rest unchecked — don't delete.** An unchecked finding posts nothing, ever, and it stays in the file as a record: on a re-run, findings already present are left untouched, so a rejected finding does not come back to be re-litigated.
- **Edit freely below the headings.** The table and each finding's prose are yours to reword, shorten, or fix. You can also reorder findings within a section (order is the only priority signal) and relabel a `##` heading — its text is used verbatim as the group label when its checked findings fold into the PR-level comment.
- **Leave the structure alone.** Don't delete a `##` heading, even over an empty section — sections are identified by position, so removing one would misroute everything below it. And don't rework a `###` heading's checkbox, numbers, or link: that line is the grammar `pr-finalize` parses.

The full grammar, with a complete worked example, lives in the `run` skill's [`SKILL.md`](skills/run/SKILL.md); how checked findings turn into an actual GitHub review is the next step.

### Check as you curate

You don't have to try posting to find out whether the file is ready. From the repository root:

```bash
pr-check    # lint REVIEW.md and report; posts nothing, changes nothing
```

`pr-check` reads `REVIEW.md` and the prepared diff and reports every problem that would stop the review from posting — a code link with a broken fragment, a finding above the first section or in a spurious fourth one, a checked inline finding whose line falls outside the diff, a checked finding folded under an unlabeled heading — each as a line formatted as `REVIEW.md:<line>:<column>: <message>`, that the Visual Studio Code terminal turns into a clickable link. If nothing is wrong, it says so.

`pr-check` runs entirely offline — no network, no GitHub, no writes — so it is instant and safe to run as often as you like while you tick boxes and edit. It shares `pr-finalize`'s parser and linter, so a file `pr-check` calls clean is one `pr-finalize` will accept; it just gives you the answer now rather than at the end of `pr-finalize`'s live-head check and GitHub round-trip.

**Want the results in Visual Studio Code's Problems panel?** `pr-check` prints the compiler-style `file:line:column: message` format Visual Studio Code parses natively, so a one-off task turns each problem into a clickable diagnostic — no extension needed. Add this to a `tasks.json` — either the reviewed repo's `.vscode/tasks.json`, or your own user tasks (**Tasks: Open User Tasks**) if you would rather not drop a file into someone else's project:

```json
{
  // See https://go.microsoft.com/fwlink/?LinkId=733558
  // for the documentation about the tasks.json format
  "version": "2.0.0",
  "tasks": [
    {
      "label": "pr-check",
      "type": "shell",
      "command": "pr-check",
      "presentation": { "reveal": "silent", "clear": true },
      "problemMatcher": {
        "owner": "pr-check",
        "fileLocation": ["relative", "${workspaceFolder}"],
        "severity": "error",
        "pattern": {
          "regexp": "^(.+?):(\\d+):(\\d+): (.+)$",
          "file": 1,
          "line": 2,
          "column": 3,
          "message": 4
        }
      }
    }
  ]
}
```

Run it with **Tasks: Run Task → pr-check** (or bind it to a key). Each run refreshes the Problems panel; the indented hint lines do not match the pattern, so every problem shows as one clickable entry. The task file is yours to place and maintain — the plugin never writes it.

### Preview, then post

From the repository root:

```bash
pr-finalize --dry-run    # parse, route, print the exact payload — posts nothing
pr-finalize              # post the review, after a recap and a terminal confirmation
```

A checked finding under Problems or Observations posts as an inline comment at its location. GitHub can anchor a comment only on a changed line, so that location must be in the diff. For a range, only the first and last line matter; the lines between them can fall outside. `pr-finalize` checks this before it posts. A location outside the diff is refused up front, and named — otherwise GitHub would reject the whole review — alongside any other problems in `REVIEW.md`, so you see the whole list before posting.

A checked finding with no location, and every checked finding under Pre-existing, is _folded_ instead: merged into the PR-level body, under its section's label.

The review's verdict follows from your curation:

- If **no** finding is checked and you have no pending review comments (see [Your own findings](#your-own-findings-draft-them-as-a-pending-review) below), `pr-finalize` posts an **approving** review.
- If **any** finding is checked, _in any section_ (even if only in Pre-existing), or you have at least one pending review comment, `pr-finalize` posts a review **requesting changes**.

Before prompting, `pr-finalize` prints a per-section recap — checked, unchecked, total — so a half-read `REVIEW.md` is visible. An approval takes a second confirmation.

Posting is a one-way step. Once the review is up, `pr-finalize` will not post a second time, and the review will not run again on this preparation. To review the PR afresh, see [Re-runs and re-preparation](#re-runs-and-re-preparation).

When the post succeeds, `pr-finalize` pauses before removing the local review artifacts: press Enter to delete them, or Ctrl-C to keep them for a post-mortem (see [Cleaning up](#cleaning-up)).

### Your own findings: draft them as a pending review

While the review runs — or while curating — you will often spot things yourself, browsing the PR on github.com. Record them with GitHub's own **Start a review** flow: pending comments are saved server-side immediately, anchored to file and line by the UI, and survive a browser restart. Just don't submit the review — `pr-finalize` picks it up.

A pending review would normally block posting (GitHub allows one pending review per user per PR), so `pr-finalize` detects yours and offers to fold it into the single review object it posts: your pending comments join the posted review exactly as you wrote them, your draft summary text (if any) is appended to the end of the review body, and the pending review is deleted from GitHub in the same step. The recap shows what is about to be imported, and everything fetched is first saved verbatim to `.pr-review-run/pending-import.json` as a recovery copy. An imported comment counts as a finding: the posted review requests changes even if no checkbox is ticked.

Declining the import aborts the post — there is no posting around a pending review; to post without importing it, submit or discard it on github.com first, then re-run. Two things cannot ride along in a single review object and are refused by name: replies to existing threads and file-level comments. Handle those in the GitHub UI. `pr-finalize --dry-run` shows the would-be import and touches nothing on GitHub.

### Re-runs and re-preparation

Within one preparation, re-running the review **stacks onto** `REVIEW.md` rather than overwriting it: findings already present are left untouched (checked or not, however you moved or edited them), and new ones are inserted **unchecked**. Because only checked blocks post, anything the merge gets wrong has no effect until you approve it.

A finalized preparation is closed: a second `pr-finalize` refuses, and so does a re-review. To start over against the current head, **re-prepare**: delete `REVIEW.md` and run `pr-review 142` again. Re-preparation wipes the snapshot, the run directory, and the marker.

### Cleaning up

A review leaves three things in your working tree: the snapshot directory (`.pr-review/`), the run directory (`.pr-review-run/`), and `REVIEW.md`. Preparation also adds a line for each to `.git/info/exclude`, so they stay out of `git status`. None of the review's artifacts are committed, and you will usually want them gone once a review is done.

`pr-finalize` offers to remove them for you: after a successful post it pauses, and pressing Enter deletes all review artifacts and prunes their `.git/info/exclude` entries. Press **Ctrl-C** instead to keep everything for a post-mortem — the post already succeeded, so nothing is lost either way.

To remove the artifacts at any other time, run `pr-cleanup` from the repository root. It does the same wipe, and:

- If the review was **posted**, it wipes without asking.
- If it was **not** posted — you abandoned it, or you are still curating — it asks first, so the work that went into a review isn't lost by mistake.

---

## How it works

### The moving parts

The commands you run yourself, from a repository root:

- **`pr-review`**, a terminal command (self-contained bash). Prepares the PR branch (fetch, snapshot, recreate base, `gh pr checkout`, rebase, confirmed force-push) and, once you press Enter, launches the sandboxed review session.
- **`pr-finalize`**, a terminal command (self-contained Python 3). Posts the curated `REVIEW.md` to GitHub as one review object.
- **`pr-check`**, a terminal command (self-contained Python 3). Lints the curated `REVIEW.md` offline and reports anything that would stop it posting — no network, no GitHub, no changes. See [Check as you curate](#check-as-you-curate).
- **`install`**, a one-time setup step (`/pr-review:install`) that puts these commands on your `PATH`. See [Installation](#installation).

And the parts `pr-review` drives for you, not meant to be invoked directly:

- **The `run` skill**: the review itself — the prompt, the six lanes, the validation pass, and the exact `REVIEW.md` grammar. Invoked as `/pr-review:run` inside the sandbox, normally launched by `pr-review`; you'd run it by hand only in an already-prepared session. Its `SKILL.md` is the spec for everything about `REVIEW.md`'s format; this README is only an overview.
- **`pr-assemble-rules`**, a self-contained Python 3 helper that `pr-review` runs during preparation. It sources the project's rule set from the PR's **base** branch into the snapshot, so the review judges against rules the PR cannot have rewritten. It shares the `PATH` shim (so `pr-review` can find it by bare name) but is never invoked by hand.

The two commands share no code. They meet at a file contract: the preparation snapshot under `.pr-review/`, plus a `posted.md` marker under `.pr-review-run/` once a review is posted.

### Why the split

Preparation needs the network and writes to `.git/config`, so it runs **unsandboxed**. The review needs neither, reads untrusted text, and so runs **sandboxed with zero egress**; its entire GitHub context is the snapshot taken before the sandbox closed. Posting needs the network again, so `pr-finalize` runs **unsandboxed** too. `pr-review` is the boundary between the first two; the file contract is the boundary between the review and `pr-finalize`.

### Artifacts

All review artifacts (`.pr-review/`, `.pr-review-run/`, and `REVIEW.md`) are hidden from `git status` through `.git/info/exclude`, maintained by the preparation, never through `.gitignore`. They never enter the project's history and never make the next preparation see a dirty tree. To remove them once a review is done — including their `.git/info/exclude` entries — see [Cleaning up](#cleaning-up).

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

- **The script is read from the PR's base branch, never from the PR.** Same rule as the project rules the review judges against — a pull request cannot rewrite it, and cannot introduce one. If a PR modifies the script, preparation says so and runs the base version anyway; if a PR _adds_ one the base does not have, preparation says so and runs nothing. Either way, **the hook only takes effect once it is on the base branch** — merge it there before expecting it to run, including the very first time you add it.
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

- **Update the plugin:** `claude plugin update pr-review@tenacom-ai-tools` picks up the latest released version. Then run `claude -p /pr-review:install` again to refresh the on-`PATH` copies: they live outside the plugin cache and do not update on their own.
- **Uninstall:** `claude plugin uninstall pr-review@tenacom-ai-tools`, then remove the `PATH` entries and the copies the setup step created:

  ```bash
  rm -f ~/.local/bin/pr-review ~/.local/bin/pr-finalize ~/.local/bin/pr-check ~/.local/bin/pr-cleanup ~/.local/bin/pr-assemble-rules
  rm -rf ~/.local/share/pr-review
  ```

  The plugin's own files are removed by `claude plugin uninstall`; only the on-`PATH` shims and their backing copies live outside the plugin and need this manual cleanup.

---

## Reference

- **`pr-review <id>`** prepares and reviews, pausing for an Enter before the review session starts; **`pr-review prepare <id>`** prepares only; **`/pr-review:run`** runs the review in an already-prepared session.
- **`pr-finalize`** posts; **`pr-finalize --dry-run`** previews the payload and posts nothing. A pending GitHub review of yours on the PR is folded into the post (and deleted), after confirmation. On a successful post it pauses to offer removing the local artifacts (Enter to remove, Ctrl-C to keep).
- **`pr-check`** lints `REVIEW.md` offline and reports what would block posting, or says it is clean; it changes nothing and needs no network.
- **`pr-cleanup`** removes the local review artifacts (`.pr-review/`, `.pr-review-run/`, `REVIEW.md`, and their `.git/info/exclude` entries); it wipes silently once the review was posted, and asks first otherwise.
- **`/pr-review:install`** puts these commands on your `PATH` (run once, at install, and again after each plugin update).
- **The `run` skill's `SKILL.md` is the spec** for the review and for the `REVIEW.md` grammar: the three lexical rules, the `###` heading shape, the checkbox-as-curation primitive, the three sections, the anchor lint, the voice, and the worked example. This README does not restate it.
