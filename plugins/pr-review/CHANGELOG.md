<!-- markdownlint-disable MD024 MD034 -->

# Changelog

All notable changes to this plugin will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Unreleased changes

### New features

### Changes to existing features

- The sandboxed review is hardened and now fails closed. If the operating-system sandbox cannot start, the review stops instead of silently running unprotected, and on Linux/WSL2 it checks up front for its dependencies (`bubblewrap`, `socat`) with a clear message if either is missing. Executed commands are now contained by the sandbox itself: the review's own files and the rest of the working tree are read-only to shell commands, so nothing a command runs can alter the review or the repository. Because that containment no longer relies on naming individual interpreters, the previous `php`/`node`/`npm`/`npx` command denials were removed; such a list could never be complete.

### Bugs fixed in this release

- The sandboxed review no longer prompts for permission on commands with shell expansions (or other constructs Claude Code's static analyzer cannot parse) — a Claude Code bug ([anthropics/claude-code#43713](https://github.com/anthropics/claude-code/issues/43713)) that defeated sandbox auto-allow. A session hook restores the sandbox as the trust boundary.
- The sandboxed review no longer prompts when an agent edits a file it just wrote (for example, revising its working notes); `Edit`/`MultiEdit` are now permitted inside the sandbox.
- Review agents no longer search the filesystem for inputs they were already handed (the diff, the changed-file list), which could waste time or trigger spurious permission prompts.
- The review's own safety rules now reliably reach every review agent — and, for the first time, the validators that double-check each finding. Previously most of those rules lived only in the skill's prose and reached the agents partially or not at all, so on a large or hostile pull request a review could occasionally run the code under review, treat leftover files from an earlier review as if they were current findings, loop on an agent that had legitimately found nothing, or be steered by instructions planted in the pull request's own description or code. The agents now receive all of these rules verbatim: never execute the reviewed code, never read leftover review files or another agent's notes, treat the pull request's own description, diff, and code as material to audit rather than commands to obey, and always write a report even when they find nothing.
- A review agent that fails to produce its report is now retried once and then reported as a coverage gap, instead of being relaunched indefinitely.
- When a review agent can read only part of a large pull request, its coverage note is now surfaced — both recorded in the session and folded into the review's verdict — instead of being silently dropped, so a partial review is never mistaken for a complete one.

### Known problems introduced by this release

## [1.0.1](https://github.com/Tenacom/tenacom-ai-tools/releases/tag/pr-review/1.0.1) (2026-06-30)

### Bugs fixed in this release

- Reviews no longer interrupt you with permission prompts for their search commands. A recent Claude Code update renamed the bundled search tools the review relied on, so its searches fell back to forms the sandbox could not auto-approve; search now uses ripgrep (`rg`), with `grep`/`find` as fallbacks, restoring prompt-free reviews.

## [1.0.0](https://github.com/Tenacom/tenacom-ai-tools/releases/tag/pr-review/1.0.0) (2026-06-29)

Initial release.
