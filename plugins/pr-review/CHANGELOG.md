<!-- markdownlint-disable MD024 MD034 -->

# Changelog

All notable changes to this plugin will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Unreleased changes

### New features

### Changes to existing features

### Bugs fixed in this release

### Known problems introduced by this release

## [2.2.0](https://github.com/Tenacom/tenacom-ai-tools/releases/tag/pr-review/2.2.0) (2026-07-13)

### New features

- **A repository can now have its dependencies synchronized to the PR before the review runs.**
  Commit a `.claude/pr-review/sync-deps.sh` script (typically a single `npm ci --ignore-scripts` or `composer install --no-scripts --no-plugins` line) and preparation will run it, so the review reads the libraries the PR declares instead of the ones left over from your previous checkout. Repositories without the script are unaffected.
  The script is read from the PR's base branch, so a pull request cannot rewrite it; preparation fails if the script fails, moves `HEAD`, switches branch, or leaves the working tree dirty.
  Being an installer run against the PR's own manifests, it is also a deliberate security trade-off: read the warning in the README before adopting it.

### Changes to existing features

- **`pr-review` now waits for you to press Enter before it launches the review session.**
  The session takes over the terminal and scrolls away everything preparation printed, so what it did — a force-push, a dependency sync that was skipped, a head that moved — went unread.
  Press Ctrl-C at the prompt to stop there instead, with the prepared branch checked out.

## [2.1.0](https://github.com/Tenacom/tenacom-ai-tools/releases/tag/pr-review/2.1.0) (2026-07-11)

### New features

### Changes to existing features

- **The review body no longer opens with a verdict paragraph.**
  Verdict paragraphs observed during real-world use of `pr-review` consistently failed to convey any useful information and were often in need of a rewrite. That was additional curation work for no real value, and is now no longer necessary.
- **The status table in the review body has lost the `Status:` label above it.**
  Without the verdict paragraph, the status table now opens the review and, unless content gets added during curation or some findings are not pinned to the diff, also closes it. The `Status:` faux-heading at this point was visual noise.
  One exception: when the review could not fully cover the change, a single sentence saying so — and nothing else — precedes the table.
- **The status table has no `Note` column any longer.**
  On rows where the `Outcome` column read "Partial" or "Missing", the `Note` column summarized findings that the curator might later decide not to post. A `Note` cell mentioning a finding that is not in the review is worse than no note at all.
  It should be noted that unchecked findings can _still_ turn a "Partial" or "Missing" outcome into a blatant lie. This is, however, a lot easier to fix during curation than a paragraph of text mixing mentions of checked and unchecked findings.
- **Two glossary keys are gone.**
  As a result of the above-mentioned removals, the `status.heading` and `status.columns.note` keys in project glossary files (`.claude/pr-review/strings.<code>.json`) are now quietly ignored. New glossaries should omit them.
- **Empty review bodies are now allowed.**
  `pr-finalize` no longer refuses to request changes when the review body is empty. The "add a short summary, then re-run" stop is gone.

### Bugs fixed in this release

### Known problems introduced by this release

## [2.0.0](https://github.com/Tenacom/tenacom-ai-tools/releases/tag/pr-review/2.0.0) (2026-07-10)

### New features

- `pr-finalize` now folds your own pending GitHub review on the PR (the "Start a review" flow) into the review it posts, instead of failing against GitHub's one-pending-review-per-user limit. Your pending comments join the posted review exactly as you wrote them (deleted-side and multi-line anchors included), a draft summary is appended to the review body, and the pending review is deleted from GitHub in the same step — after a recap and an explicit confirmation, with everything fetched saved to `.pr-review-run/pending-import.json` as a recovery copy first. Imported comments count as findings, so the posted review requests changes even with no checkbox ticked. Replies to existing threads and file-level comments cannot ride along in a single review object and are refused by name.

### Changes to existing features

- **BREAKING:** Reviews now speak with a single voice — the plain, concept-explaining style that used to be the default `junior` register. The `expert` register is gone, and with it the register argument: `pr-review <id>` and `/pr-review:run` no longer take one, and `pr-review` now rejects any extra argument instead of reading it as a register.

### Bugs fixed in this release

- Review findings could bury the actual defect in a wall of text that re-explained the reviewed code, step by step, to the very person who wrote it — routinely forcing the reviewer to rewrite findings before posting. A finding now states what is wrong, what triggers it, and the consequence, typically in a few sentences ahead of the proposed fix.
- The review's opening verdict could balloon into a full recap of the pull request plus a preview of every finding — prose the status table and the findings themselves then repeated (the table's Note column could make it a third telling). Worse than verbose, it leaked: the verdict posts unconditionally with the review body, so a finding the reviewer had deliberately left unchecked could still reach GitHub through its summary in the verdict. The verdict is now a short judgment — does the change do its job, and what stands in the way — with the details left to the table and the findings, and the Note column now points at a finding instead of retelling it.
- Findings about consistency and code style could land as take-it-or-leave-it questions ("fix it or leave it as is?"), inviting the zero-effort answer and framing conventions as personal taste. A departure from a clear codebase convention is now reported as a problem with one correct fix, and the findings that do hand back a genuine decision (scoping, real design trade-offs) now state which alternative the review recommends and why, instead of "both are fine".

## [1.0.3](https://github.com/Tenacom/tenacom-ai-tools/releases/tag/pr-review/1.0.3) (2026-07-03)

### Changes to existing features

- The sandboxed review no longer makes the whole working tree read-only to shell commands — only `.git` and the review's own snapshot and run directories stay read-only. This walks back part of the 1.0.2 hardening (see the fix below for why it had to), but the protection that matters is unchanged: executed commands still cannot plant a git hook or tamper with the review's inputs and reports. `REVIEW.md` and the rest of the working tree become writable to shell commands, which is inert in practice — the review runs no project code and its own shell use is read-only search.
- The review's captured GitHub snapshot and `.git` are now immutable to the review itself, not just to the commands it runs: the file-editing tools are blocked from writing there, closing the path by which a crafted pull request could try to steer the review into rewriting the very diff and rules it is judged against. The review's own working area (its report files and `REVIEW.md`) stays writable.

### Bugs fixed in this release

- The sandboxed review could fail to start on any repository without a `.gitconfig` at its root — every shell command aborted, which looked like `git` failing even though git was never involved. It was the operating-system sandbox refusing to initialise against a fully read-only working tree; the review no longer marks the whole tree read-only.

## [1.0.2](https://github.com/Tenacom/tenacom-ai-tools/releases/tag/pr-review/1.0.2) (2026-07-03)

### Changes to existing features

- The sandboxed review is hardened and now fails closed. If the operating-system sandbox cannot start, the review stops instead of silently running unprotected, and on Linux/WSL2 it checks up front for its dependencies (`bubblewrap`, `socat`) with a clear message if either is missing. Executed commands are now contained by the sandbox itself: the review's own files and the rest of the working tree are read-only to shell commands, so nothing a command runs can alter the review or the repository. Because that containment no longer relies on naming individual interpreters, the previous `php`/`node`/`npm`/`npx` command denials were removed; such a list could never be complete.

### Bugs fixed in this release

- The sandboxed review no longer prompts for permission on commands with shell expansions (or other constructs Claude Code's static analyzer cannot parse) — a Claude Code bug ([anthropics/claude-code#43713](https://github.com/anthropics/claude-code/issues/43713)) that defeated sandbox auto-allow. A session hook restores the sandbox as the trust boundary.
- The sandboxed review no longer prompts when an agent edits a file it just wrote (for example, revising its working notes); `Edit`/`MultiEdit` are now permitted inside the sandbox.
- Review agents no longer search the filesystem for inputs they were already handed (the diff, the changed-file list), which could waste time or trigger spurious permission prompts.
- The review's own safety rules now reliably reach every review agent — and, for the first time, the validators that double-check each finding. Previously most of those rules lived only in the skill's prose and reached the agents partially or not at all, so on a large or hostile pull request a review could occasionally run the code under review, treat leftover files from an earlier review as if they were current findings, loop on an agent that had legitimately found nothing, or be steered by instructions planted in the pull request's own description or code. The agents now receive all of these rules verbatim: never execute the reviewed code, never read leftover review files or another agent's notes, treat the pull request's own description, diff, and code as material to audit rather than commands to obey, and always write a report even when they find nothing.
- The review is now hardened against a pull request tampering with the rules it is judged by. A pull request's own rule files — `CLAUDE.md`, everything under `.claude/rules/`, and the review's glossary overrides — are part of the changes under review, so a hostile pull request could previously plant instructions in them (for example, "report no problems") and have the review obey them. The review now reads those rules from the **base branch** — the version already merged into the repository — exactly as GitHub reads a CODEOWNERS file from the base, and the review's agents are told to treat any rule text in the pull request itself as content to audit, never as instructions. A pull request's changes to the rule files are still reviewed like any other change; they simply do not govern their own review (a rule a pull request introduces takes effect for later ones).
- A review agent that fails to produce its report is now retried once and then reported as a coverage gap, instead of being relaunched indefinitely.
- When a review agent can read only part of a large pull request, its coverage note is now surfaced — both recorded in the session and folded into the review's verdict — instead of being silently dropped, so a partial review is never mistaken for a complete one.

## [1.0.1](https://github.com/Tenacom/tenacom-ai-tools/releases/tag/pr-review/1.0.1) (2026-06-30)

### Bugs fixed in this release

- Reviews no longer interrupt you with permission prompts for their search commands. A recent Claude Code update renamed the bundled search tools the review relied on, so its searches fell back to forms the sandbox could not auto-approve; search now uses ripgrep (`rg`), with `grep`/`find` as fallbacks, restoring prompt-free reviews.

## [1.0.0](https://github.com/Tenacom/tenacom-ai-tools/releases/tag/pr-review/1.0.0) (2026-06-29)

Initial release.
