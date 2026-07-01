---
name: run
description: Review the prepared PR branch against full local source with zero network — all GitHub context comes from the preparation's snapshot in .pr-review/ — verify it fulfils its stated purpose, and write the findings to REVIEW.md — a structured file whose body is the PR-level review comment and whose ###-headed blocks are findings that post only once a human checks their checkbox
argument-hint: "[expert]"
allowed-tools: Bash(git rev-parse:*), Bash(git merge-base:*), Bash(rg:*), Bash(grep:*), Bash(find:*), Bash(ugrep:*), Bash(bfs:*), Read, Grep, Glob, Task, Write, Edit, MultiEdit
disable-model-invocation: true
effort: max
---

Review the prepared pull request on the current branch against the full local source and write the findings to `REVIEW.md` in the repository root. The filename is **fixed** — the PR number lives in the file's frontmatter and in the checked-out branch, never in the filename. The PR number is **never** an argument — the checked-out `pr/<id>` branch is the single source of truth for which PR is under review, and `<id>` (the digits after `pr/`) is read from that branch name (see Precondition). The one optional argument selects the **register** — how findings are explained (see Register): `expert`, or `junior`/omitted for the default. Any other value (a PR number typed out of habit, say) is ignored, and the register stays `junior`; the branch still decides which PR.

**This review makes no network calls — no `gh`, no fetching, nothing.** Everything it needs from GitHub — the PR's title, body and metadata, every referenced issue, and the canonical diff — was captured by the preparation into `./.pr-review/` at the repository root (hidden from `git status` by the preparation, like the run directory). That snapshot plus the checkout on disk is the entire review surface. Reviewing the snapshot as of preparation, not whatever the PR mutated into since, is deliberate — the same determinism argument as the one canonical diff — and the sandbox this review normally runs in has no network anyway. If something appears to be missing from the snapshot, do not try to fetch it: note it and proceed.

## Precondition

Confirm the tree is actually prepared, do not assume it.

1. Read the current branch: `git rev-parse --abbrev-ref HEAD`. It **must** match `^pr/\d+$`. If it does not, the tree is not prepared: **stop** and tell the user to run `pr-review <id>` from a shell — with the number of the PR they want to review — which prepares `pr/<id>` (checkout, rebase, confirmed force-push) and relaunches this review sandboxed. Do not prepare the tree yourself, and do not ask them for a PR number here; the script takes it.
2. Derive `<id>` as the digits after `pr/` in the branch name. This is the only source of the PR number; every later step uses it, and it appears in no argument.
3. Read `state.json` from the snapshot directory. If it is missing, the preparation never completed (it is written last, as the completeness marker): **stop** and tell the user to re-run `pr-review <id>` from a shell. Its `prId` must equal `<id>` from the branch; a mismatch means the snapshot belongs to another PR: **stop**, same remedy. Note `baseBranch`, `baseSha`, and `head` from it.
4. The tree must be exactly the prepared state. `state.json`'s `head` must equal `git rev-parse HEAD`, the local base branch (`baseBranch`) must exist, and `git merge-base --is-ancestor <baseBranch> HEAD` must succeed. Any mismatch means the tree moved after preparation — and the preparation's guarantee (force-push made the PR head on GitHub equal the prepared head) no longer covers what is on disk, so every link this review writes would lie: **stop** and tell the user to re-run `pr-review <id>` from a shell. Anchors that lie are worse than no review.
5. If `REVIEW.md` exists at the repo root, this run will **merge into it** (see Additive re-runs), so it must belong to this preparation: its frontmatter `pr` must equal `<id>` and its frontmatter `head` must equal `state.json`'s `head`. A mismatch means the file survived from another PR or another preparation: **stop** and say so — deleting the file is the user's call, never yours. Check this here, before any agent runs, not at write time. Whether or not the file exists, fix **this run's number** now: frontmatter `runs` + 1 when `REVIEW.md` exists, 1 when it does not. The run directory's filenames carry it (see The run directory), so it must be known before dispatch — and the merge bumps `runs` to exactly this value.
6. Check the run directory for a posting marker: `rg --files ./.pr-review-run -g posted.md`. If it returns a path, `pr-finalize` has already posted this preparation — `REVIEW.md` is kept for follow-up, but the preparation is **closed**. **Stop** and tell the user to re-prepare (`pr-review <id>` from a shell, after deleting `REVIEW.md`) to review the current head afresh. Re-reviewing a finalized preparation would merge new findings into a file that no longer matches what was posted. (The shell entry point refuses this too; the check lives here as well because `/pr-review:run` from an open session does not pass through it.)

## Strategy: review in context (get the big picture)

The PR's changes are the snapshot's canonical diff (`baseSha..head`). That diff tells you only _what_ changed. The reason the tree was checked out and rebased is so you review the change _in context_: the surrounding code is on disk at the rebased state — use it. A hunk that looks correct in isolation is routinely wrong against the contract of what it calls, or duplicates something that already exists, or breaks a pattern every sibling file follows.

And before judging whether the code is _good_, judge whether it is the _right_ code: does it actually do what the PR set out to do? Good code that does not resolve its issue is not a passing review.

## Agent assumptions (all agents and subagents)

- All tools are functional. Do not test tools or make exploratory calls. Make sure this is clear to every subagent that is launched.
- Only call a tool when it is required to complete the task, with a clear purpose.
- **History is not review surface.** The review surface is the checkout at HEAD plus the snapshot, nothing else. Never run `git log`, `git show`, or `git diff`: the PR branch's intermediate commits contain deltas that later commits cancelled, and quoting them produces findings about code that does not exist at HEAD — the worst kind of ghost, because it once was real. The only git commands this review runs are `git rev-parse` and `git merge-base`, both in the precondition.
- **`REVIEW.md` is never review input.** A previous run's file may sit at the repo root; no agent or validator reads, searches, or cites it — it quotes old diffs and reads exactly like code. The one exception is the merge (step 7), in the main agent, after every finding has been validated: there it is curation state, never code. The snapshot in `.pr-review/` is input (the diff, the PR text, the issues), never subject: report no findings against its contents.
- **Bash commands must be single, plain, literal commands** — no command substitution, no variable expansion, no pipes, no `&&`/`;` chaining, no `-exec`. Anything text-shaped goes through Read or the fixed search shapes below. (A review must stay legible and auditable: one command, one purpose, matchable at a glance against the closed vocabulary — compound and expanded forms hide what actually runs, and `-exec` is arbitrary execution wearing a search flag.)
- **Searching is `rg` (ripgrep), in fixed shapes.** On native builds the Grep and Glob tools do not exist, so search is a bash command under the plain-commands rule. Content search: `rg -n <pattern> <path>`, adding `-F` whenever the pattern is a literal string — most are (`rg` recurses into a directory by default, so there is no recurse flag to add). File finding: `rg --files <dir>`, narrowed with `-g <glob>`. Nothing else: never pipe or post-process the output, never re-run a search fancier — read the matches with Read. Keep regex patterns literal or near-literal, never nested quantifiers: `rg` is backtracking-immune, but the fallbacks below are the embedded `ugrep`, which runs inside the agent's own process where a catastrophically backtracking pattern takes the session down with it. **If a search command is missing, do not escalate to pipes or loops to compensate** — the identical plain shapes work with `grep` (content) and `find` (file finding), which current builds wire to the same embedded search tools; `rg`, `grep`, `find`, and the legacy `ugrep`/`bfs` names are all allow-listed, so a build that renames the embedded tools degrades to at worst a single permission prompt, never a missing-command stop that would abort the review. The review's whole bash vocabulary stays tiny and read-only: `git rev-parse` and `git merge-base` in the precondition, one search command for everything else. Where the Grep and Glob tools do exist (npm and Windows builds), prefer them over the bash forms — same shapes, same restraint.
- **The review never executes the code it reviews** — no `php`, no `node`, no interpreter, runner, or test invocation, however diagnostic the intent. Each reason is sufficient alone: `require`-time code runs the moment an autoloader loads, the review surface is attacker-influenceable (fork PRs), and inside the sandbox the whole working tree — snapshot, run files, `REVIEW.md` — is writable by any bash child, so executing project code hands the review's own ground truth to the code under review. Runtime results depend on the local interpreter, extensions, and vendor state — an unsanctioned third review surface beside checkout and snapshot. And the epistemic standard here is **Read**: a dependency's behavior lives in its vendored source on disk, in the exact version the project pins — "how does `Carbon::parse` treat a bare numeric string?" is answered in `vendor/nesbot/carbon`, not by running it. When reading cannot settle a behavioral question, the finding **states the question and the experiment that would settle it**: running experiments against a PR is the human reviewer's decision, like everything else posted under his name.

## The run directory

Subagent results travel as **files, never as messages**. The Task notification channel can silently drop a completion — a run that waits on it can stall forever — so every subagent's final act is writing its report file into the run directory, and the main agent collects from the filesystem: it knows the complete expected set at dispatch, so collection is confirm-and-Read, never wait-and-hope. The Task return value is never the report — it is a **one-line receipt**: the file path, the finding count, and the write status. The file carries the data; the return carries status. A failed Write thus surfaces at the doorbell ("Write FAILED: …") instead of as a hole at collection time; a count that disagrees with the file's contents flags a truncated write; and a lost notification loses one line of status, nothing more.

- The directory is `./.pr-review-run/` at the repository root — deliberately **not** under `.git/`, which Claude Code treats as a protected write path and prompts on every Write there regardless of allow rules. The preparation cleared and recreated it (and hid it from `git status` via `.git/info/exclude`): its lifetime is the **preparation**, not the review. Files from earlier runs of the same preparation stay — they are the human's post-mortem record — and a re-prep wipes them, correctly, because their line numbers die with the tree they were measured against.
- Filenames are a closed grammar, two shapes: `r<run>-a<agent>.md` for a lane's report — the same run and agent numbers the heading grammar carries, one identity scheme end to end — and `r<run>-v<n>.md` for a validation report, `<n>` progressive in dispatch order. Validation files carry no agent number deliberately: a validator may carry findings from any mix of lanes, so an agent number there would be a lie waiting to happen.
- **No subagent reads the directory.** Each writes its own file and touches nothing else there; only the main agent collects. Files from earlier runs are **never review input** — the same clause as `REVIEW.md`, for the same reason: they quote old text and read exactly like findings. They exist for the human's post-mortem and the current run's collection, nothing else.

## Steps

1. From the snapshot's `pr.json`, note the author, the PR `state` (if closed or merged, note it but proceed; the user prepared it deliberately), the `url`, and the **natural language of the title and body** — the review file must be written in that language. Resolve the **glossary** for that language now (see Language and strings): a built-in for `en`/`it`/`es`, a project `.claude/pr-review/strings.<code>.json` otherwise, or — failing both — an improvised translation of the English glossary, flagged as such in the session.
2. Establish the PR's **intent** from two sources, combined — never one or the other:
   - **The PR text itself, always.** Read `pr.json`'s title and body for everything the author declares they did — not just a headline goal, but every stated change, including asides ("also fixed this bug while I was here", "dropped the dead flag") and any bulleted list of modifications. All of it is intentional, whether or not an issue mentions it.
   - **Referenced issues.** The preparation captured every issue the PR references — the Development-panel links and every `#N` mention — as `issue-<n>.json` files in the snapshot, deliberately over-inclusively. Read each one and judge its role: an issue the PR closes or fixes carries requirements / acceptance criteria; a merely-mentioned one is context. If the text references a number with no captured file, the preparation could not fetch it (a PR reference, or no access) — do not fetch it yourself; note it only if it matters.

   Assemble an **intent brief** that _unions_ both: the requirement-bearing issues **and** the changes the PR text declares. A change stated in the description is intended even when no issue covers it, and must not later be treated as unrelated scope. If the PR references no issues, the intent brief is simply everything the text declares.
3. Establish what changed. The **canonical diff** is the snapshot's `canonical.diff`, with the changed-file list beside it in `changed-files.txt` — both computed once by the preparation, post-rebase. Read them; **never re-derive the diff**: every agent reads that same file, so all six review an identical, correctly-scoped snapshot instead of each re-deriving one and risking a different base or flags. Then parse the diff's `@@ -a,b +c,d @@` hunk headers — the `+c,d` side — into the **changed ranges**, per file, once. That parsed list is the single source of truth for diff membership: it re-derives every finding's in-diff flag at aggregation (step 6) and lints every anchor at write time (see The anchor rule). One parse, two consumers; the flags agents report are advisory only.
4. Assemble the project rule set the standards agents will audit against. **Do not assume a subagent can reach it by reading `CLAUDE.md`**: `Read` returns literal text — it does not expand `@imports` or load `.claude/rules/` — and subagents do not reliably inherit the session's loaded memory. Gather it explicitly, here, in the main agent:
   - Read the `CLAUDE.md` hierarchy from the repo root down to the directories containing changed files.
   - For every `@import` line in those files, read the imported file too, recursively.
   - Read every `.claude/rules/**/*.md`. A rule file with no frontmatter applies repo-wide; a rule file with a `paths:` frontmatter applies only to changed files matching its globs — record that scope, the rule agent needs it.

   The fully-expanded, assembled text is what you pass to the agents below. Pass text, not paths.
5. Launch 6 subagents in parallel — one per lane below. **Your role here is dispatch, not review.** Do not analyse the diff for findings yourself before launching them, and never seed a subagent's prompt with your own hypotheses or a list of things you suspect: that anchors the agent onto your guesses and collapses the independent coverage that makes six sweeps find more than one. You assemble context and dispatch; the agents find. (The cross-checking you might be tempted to do up front is the validation pass in step 6 — after independent gathering, which is the only safe order.)

   Each subagent's prompt must contain, explicitly:
   - its lane and charter (from the list below), and nothing drawn from the other lanes;
   - the **intent brief** (step 2) and the **applicable rule set** (step 4);
   - the **full list of changed files** (step 3), with the instruction to walk _every one_, working from the full checkout on disk — not just the diff hunks;
   - the **path to the canonical diff** (step 3): the agent reads that file rather than rebuilding the diff. It is the _index of what changed_ — the review surface is still the full checkout, never the diff alone;
   - **exhaustive, not illustrative**: report every finding it can substantiate in its lane, not the most salient one or two — recall is the point, and the validation pass culls the excess;
   - **pre-existing findings are reported, not discarded**: a defect in a file the PR does not touch, or in a touched file but that no hunk causes or mirrors, is still a finding — returned **tagged pre-existing**. These are gathered _incidentally_, while the lane's own work surfaces them; the charter never becomes a repo-wide sweep, so the agent reports what it stumbles on and does not go hunting;
   - the **agent assumptions** above (tools work; no exploratory calls);
   - its **output file**: `./.pr-review-run/r<run>-a<agent>.md` — writing its complete report there, in the fixed return format, **in one single Write as its final act** — never incrementally, never edited afterwards — is how results are delivered; the Task return is **one line only** — file path, finding count, write status — never the report itself (the report in the return would only duplicate, in the orchestrator's context, content the collection step Reads from the file anyway);
   - a fixed return format — one finding per entry: the problem, its exact location (file and line range), whether that location falls inside a changed range of the canonical diff, a pre-existing tag where it applies, and the fix — so you can aggregate without re-interpreting.

   The six lanes (each agent works from the full checkout, never just the hunks):
   - Agent 1 — correctness in context: for each changed function, read the definitions of what it calls and the callers it affects; check edge cases, error paths, and invariants that only surface outside the hunk.
   - Agent 2 — reuse / single source of truth: search the codebase for existing functionality the PR reimplements or duplicates (helpers, abstractions, patterns). Flag reinvented wheels and duplicated truth — but shared _shape_ is not shared _meaning_: two types or components with the same structure yet different semantics (a date range vs a timestamp range; an id vs a count) are not duplication. Flag it only where responsibility and meaning coincide, not merely the layout of the data.
   - Agent 3 — internal-standard adherence: compare the new code against structural/architectural standards and invariants the codebase enforces. Flag deviations in pattern, naming, and layering, and any invariant left to convention where the codebase enforces it structurally. But a merely _prevalent_ pattern is not an enforced standard: if a convention is followed by most-but-not-all siblings with no explicit rule behind it, the codebase is inconsistent — that is an Observation, not a Problem. Watch for migrations in progress, where the newest code departs from the old majority on purpose (e.g. dropping a flag that has become the framework default); prefer an explicit rule over a head-count, and when unsure, defer rather than flag.
   - Agent 4 — rule compliance: audit the changed code against the assembled rule set, honoring each rule's scope (repo-wide rules everywhere; `paths:`-scoped rules only on the files they match). Quote the exact rule text when flagging. **Findings whose substance is textual surface** — spelling, grammar, translation, terminology, diacritics — **are out of this lane even when a rule file mandates them**: agent 6 owns the textual surface, rules included. Audit a language-policy rule file only for its non-textual clauses, if it has any.
   - Agent 5 — purpose & completeness: using the intent brief, judge whether the change does its job. Work from the full checkout, not just the diff — a requirement may be satisfied by code the diff only touches indirectly. For each linked-issue requirement **and each change the PR text declares**, decide **fully addressed / partially addressed / not addressed**, and cite the code that does (or fails to) satisfy it. Then flag as **scope-beyond** only those changes in the diff that are declared _nowhere_ — neither in a linked issue nor in the PR text. A change the author mentions in the description, however casually, is intentional and is _not_ scope-beyond; it belongs in the addressed/not-addressed list above. Scope-beyond is not a defect; surface it so the reviewer knows it is riding along undeclared.
   - Agent 6 — textual surface: spelling, grammar, translation. Read for surface-level text defects only — this is not a second correctness agent and it judges no logic. Walk every changed file's full content: comments, doc-comments, string literals, identifier names, and all user-facing text including i18n resource values. Flag misspellings; grammatical errors; doubled words; wrong or missing diacritics (Italian `è`/`perché`/`qualità` and the like); agreement errors (subject/verb, gender, number); mistranslations and wrong-language text where a specific language is expected; and typos in identifiers (a misspelled symbol is a permanent defect). Judge each target language of a human-facing string or i18n entry on its own terms. When a flagged item is also mandated by a rule in the assembled rule set (a language-policy file, say), **quote the exact rule text** just as agent 4 would — the citation belongs to the finding, not to the lane. Do **not** flag established domain vocabulary, product or API names, deliberate abbreviations, or approved foreign-language technical nouns the rule set sanctions — a codebase may mix languages by policy (technical terms in one language inside prose in another), so a word that could be either a typo or intentional jargon is checked against the rest of the repo first and deferred if used consistently elsewhere. Every find here is a Problem (one correct resolution); return them in the standard finding format, and when one fix spans several languages list each language as its own item.

   **Collect lane reports from the run directory, never from Task returns.** All six filenames are known from dispatch; Read each file. A lane whose Task result went missing but whose file exists completed fine — the file is the truth. A lane with neither result nor file actually died: relaunch that one lane with the same prompt and the same filename (it overwrites only its own partial), and never wait on a notification that may already be lost.
6. Validate. For each finding, launch a subagent that confirms it against the actual code with high confidence (the "undefined" symbol really is undefined; the "duplicated" helper really exists and is equivalent; the cited rule is in scope and actually broken; a requirement reported unmet really is absent from the change and not satisfied elsewhere in the checkout; a flagged misspelling is a genuine error and not domain vocabulary or an approved foreign-language technical term). **Ground truth is Read, never the finding's own quotes**: the validator must Read the cited file at the cited lines and compare what is actually there against the claim — a finding whose quoted code Read cannot reproduce at HEAD is dead, whatever its story. (For absence findings — a missing translation, an unhandled case — Read the locus and confirm the absence.) Pre-existing findings pass the same cull — the tag exempts nothing. Drop anything that does not survive validation.

   Validators follow the run-directory protocol too: number them progressively at dispatch — whatever set of findings each one carries — and each writes its verdicts to `./.pr-review-run/r<run>-v<n>.md` in one single Write as its final act, in a fixed verdict format (finding, confirmed / dropped / corrected, the corrected location where it applies), returning only the one-line receipt. Collect exactly as in step 5: from the files, with the same relaunch rule for a validator that left neither result nor file.

   Then, for every survivor, **re-derive its in-diff status yourself** against the step-3 changed ranges — the agent-reported flag is advisory. A finding whose claimed location falls in no changed range is not dropped for that: it is **reclassified** — routed by the causality rules of The anchor rule, which usually means a located block under the third section (`Pre-existing`) — and never promoted to an anchored Problem on the strength of a wrong flag. Content that fails Read dies; routing that fails the ranges moves.
7. Assemble this run's complete output — frontmatter, body, sections — **in the language of the PR post**, exactly as specified in The review file below: the **run document**. Every checkbox in it is unchecked — checking is the human's act, never the machine's. Then write:

   - No `REVIEW.md` at the repo root → first run of this preparation: write the run document as `REVIEW.md` (`runs: 1`).
   - `REVIEW.md` exists (the precondition already matched it to this preparation) → **merge** the run document's findings into it per Additive re-runs below: skip what is already there, insert what is new — unchecked. The curated file is the human's; the machine only adds. One file, one write.

   Posting is a separate, human-gated step — the **`pr-finalize`** tool, run from a shell after curation (see No posting on GitHub). It posts the body as the PR-level review comment and each **checked** block as a comment — located findings inline, the rest folded into the body — then leaves a `posted.md` marker that closes the preparation. The review here never posts.

## Language and strings

`REVIEW.md` is written **in the natural language of the PR's title and body** (step 1) — never the language of this spec, nor any one project's house language. Everything human-facing in the file is in that language: the verdict, every finding's prose, the status table, and the section headings. The author reads the review in the language they wrote the PR in.

Most of that text is free prose you write directly in the target language. A small, fixed set of **load-bearing literals** comes instead from a **glossary**, so they stay identical across runs — the merge recreates a missing `##` heading "in the file's language" (see Additive re-runs), and a human curator must see the same labels every time. The glossary fixes exactly these and nothing else: the three section headings, the status faux-heading, and the status table's outcome labels and column headers.

A glossary is a JSON object of this shape — and an override file (below) holds exactly the same object. The three **built-in glossaries** follow; **use them verbatim, never re-translate them.**

English (`en`):

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

Italian (`it`):

```json
{
  "sections": { "problems": "Problemi", "observations": "Osservazioni", "preexisting": "Preesistenti" },
  "status": {
    "heading": "Stato:",
    "outcomes": { "ok": "OK", "partial": "Parziale", "missing": "Mancante" },
    "columns": { "requirement": "Requisito / Modifica dichiarata", "outcome": "Esito", "note": "Nota" }
  }
}
```

Spanish (`es`):

```json
{
  "sections": { "problems": "Problemas", "observations": "Observaciones", "preexisting": "Preexistentes" },
  "status": {
    "heading": "Estado:",
    "outcomes": { "ok": "OK", "partial": "Parcial", "missing": "Ausente" },
    "columns": { "requirement": "Requisito / Cambio declarado", "outcome": "Resultado", "note": "Nota" }
  }
}
```

**For any other PR language**, read `.claude/pr-review/strings.<code>.json` from the repo root, where `<code>` is the language's ISO 639-1 code (e.g. `fr`, `de`, `pt`), and use it as the glossary. That file is the **consuming project's** to provide — the plugin ships none (a plugin cannot ship rules to its users). Precedence: a project file present for a built-in code **overrides** the built-in, so a project can tune terminology. If neither a built-in glossary nor a project file covers the PR's language, **translate the English glossary above yourself**, use it consistently for this run, and **say so in the session** — note that the labels are improvised, not canonical, so the project can add a `strings.<code>.json` to pin them.

Prose conventions **beyond these literals** — grammatical gender and declension of domain terms, terminology, register, tone — are **not** the glossary's concern. They come from the project's `.claude/rules/**` (assembled in step 4) like any other rule, or from your own command of the language. The glossary fixes only the structural labels the machine routes by and the human navigates by; everything else about writing good target-language prose lives where all other project conventions live.

## The review file

### The grammar — three lexical rules

After the frontmatter (stripped before any other parsing), the whole file obeys three rules; everything else is content:

- The **body** runs from the top of the file to the **first heading of any level**. It posts as the single PR-level review comment.
- A **`###` heading is one finding's metadata — it never posts.** Its fixed shape (see below) carries a checkbox, the run number, the agent number, and — for a located finding — exactly one relative file link. Each `###` block — the prose below the heading, until the next heading or end of file — is exactly **one comment**, and **only checked blocks post**: a checked located block under Problems/Observations posts inline at its location; a checked locationless block, and every checked block under Pre-existing, is folded by the posting step into the PR-level comment under its section's heading text as the label. An unchecked block posts nothing, ever.
- **`##` headings classify and label.** The three sections are **positional** — the 1st, 2nd and 3rd `##` heading are Problems, Observations, Pre-existing _whatever their text reads_ — so the posting step routes by that ordinal, and all three are always present, in order, even when empty (see Classification). The heading **text** is the human-facing label: when a section's checked blocks fold into the PR-level comment, the poster lifts the text **verbatim** as their group label, so the human relabels a group by editing its heading. A located block posting inline carries no group label. Prose between a `##` heading and its first `###` — a **section preamble** — is copied verbatim ahead of that group when (and only when) the section contributes a folded finding; the review writes none, but the human may add one during curation.

Corollary on links: relative links exist **only** inside `###` headings; every other link in the file — evidence inside a block, a pointer in a body paragraph — is a **GitHub permalink** (the body and the block prose post to GitHub, where a relative link resolves to nothing).

### Frontmatter

```yaml
---
pr: 142            # the digits of the checked-out pr/<id> branch
repo: owner/repo   # the base repo, parsed from pr.json's url
head: <sha>        # git rev-parse HEAD (== state.json head) — the reviewed code, which is also the PR head on GitHub (preparation force-pushed it; the precondition verified it)
base: <sha>        # state.json baseSha — the base the canonical diff was taken against
runs: 1
---
```

Provenance only — it is stripped before the file is parsed and never interacts with the body/heading boundaries. Record SHAs, never branch names, and store nothing composed from these values (no permalink prefix — that would be a second copy of `head`). `runs` starts at `1` and is bumped by every merge (see Additive re-runs): it counts how many runs have fed this file within the current preparation.

### Body

In order, blank-line separated. Each piece below is **exactly one paragraph** unless stated otherwise. A slot with nothing to say is **omitted entirely** — no "nothing to report" filler. **Findings never live in the body** — exactly two slots:

- **The verdict** — one paragraph, first thing in the file, **no heading and no label above or before it** (no "Summary:", "Verdict:", or any equivalent in the PR's language). One to three sentences on whether the change does what it set out to do and what stands in the way. Describe the _state of the work_, never the author, and do not recap what the change does — they wrote it, they know.
- **The status faux-heading** — the glossary's `status.heading`, rendered bold (English `**Status:**`, Italian `**Stato:**`), deliberately **not** a `##`/`###` heading: a real heading here would end the body and orphan everything after it. Below it, the table: one row per linked-issue requirement and per change the PR text declares; the outcome is the glossary's `status.outcomes` value with its emoji — `✅ <ok>` / `⚠️ <partial>` / `❌ <missing>` (English `✅ OK` / `⚠️ Partial` / `❌ Missing`); a one-short-sentence reason. Its column headers are the glossary's `status.columns`. When the reason is itself a finding, point at it **by its location link text, as plain unlinked text** — "see app-routing.module.ts L34" — never by run/agent numbers (provenance and identity, not references for humans) and never as a link (a relative link outside a `###` heading breaks the grammar; a permalink would point at code, not at the finding). After the table, if any: a bullet list of changes found in the diff but declared nowhere — flagged for alignment, not as faults.

The faux heading is a **pinned literal from the glossary** (`status.heading`); do not paraphrase it — keep the glossary's exact term so it stays a stable, non-heading marker. Cross-cutting and pre-existing findings, formerly body paragraphs, are `###` blocks now — locationless, and under the third section (`Pre-existing`), respectively. The posting step folds the checked ones back into the PR-level comment, each group under its `##` heading text used **verbatim** as the label — so a label like "Pre-existing, out of scope" is the heading the human edited to, not vocabulary baked into the poster.

### `###` blocks — one finding each

The heading is the finding's metadata line — checkbox, run number, agent number, location — single-space separated, and its shape is fixed:

```text
### [ ] <run> <agent> [<basename> L<start>[-L<end>]](./<path>#<start>)   (located)
### [ ] <run> <agent>                                                    (locationless / cross-cutting)
```

so a concrete located heading reads `### [ ] 1 1 [foo.service.ts L52](./projects/app/src/foo.service.ts#52)`.

- **The checkbox.** The machine always writes `[ ]` and never checks, unchecks, or removes one. The human curates by _checking_ the findings they endorse (`[x]`; consumers of the file accept the `x` in either case) instead of deleting the ones they reject: checked posts, unchecked stays in the file as memory and posts nothing, ever. This is what makes re-runs safe without tombstones — a re-offered or duplicated finding arrives unchecked, so it is inert until a human says otherwise.
- **The run number** — provenance: the value of frontmatter `runs` at the run that inserted the block. After a merge, the highest run number marks the new arrivals — the human's re-curation diff.
- **The agent number** — the lane (1–6) that produced the finding. Agent number **plus location is the finding's identity**: the merge dedupes located findings by that pair and by nothing else. Locationless findings have no machine-checkable identity and are never machine-deduped; and the same defect refound by a different lane lands as a duplicate. Both are deliberate — deduping those is the human's job, and the duplicates arrive unchecked, so the cost is reading, never posting.
- **The location link.** The link **text** is the file's basename plus the line range. The link **target** is the repo-root-relative path plus a fragment that is the **bare start line number** — `#52`, never `#L52`. The bare number is a VS Code requirement: with the `L`, the fragment is an unknown anchor and the cursor lands at line 1 — useless at line 1547; without it, clicking the heading lands on the line. Both halves are load-bearing and must agree: a later consumer takes the _path_ from the target and the _range_ from the text. These links resolve only because `REVIEW.md` sits at the repo root — that location is part of the contract. The link is **omitted entirely for a cross-cutting finding**: no single line is the finding, so the heading ends at the agent number and the posting step routes the checked block to the PR-level comment instead of inline.

- **One block per finding, one finding per block.** A heading carries its four fields and nothing else — no numbering beyond them, no title prose.
- The prose below the heading is the comment body, written **as if it already sits at that line** — because once posted, it does. Never open with coordinates ("In `foo.service.ts` L52…" is dead weight the format already carries); lead with the cause or the symptom. (A locationless block posts into the PR-level comment: same rule, lead with the substance.)
- For a Problem — **Pre-existing included** — the **fix is the block's last paragraph**, on its own line after a blank line — skimmable without labels. No `**Problem:**`/`**Fix:**` prefixes anywhere (in any language): position already encodes role (the heading is the where, the prose is the what, the last line is the remedy). A Pre-existing fix reads **identically to any other fix** — same shape, same position, and no scope or scheduling preamble ("separately:", "to fix later:", and kin): the third section's heading already says, once, everything those words would repeat per finding. Write it ready to be lifted **verbatim** into the issue or follow-up PR it will likely become — a fix that opens by discussing scheduling is precisely not liftable.
- For an Observation, the block ends with the choice being handed back — the alternatives, and the question.
- Evidence pointing _elsewhere_ (the caller that breaks, the twin that survives, the rule text's source) goes inline in the prose as GitHub permalinks.
- When one finding points at several parallel things — the same fix across languages, the call sites to unify — render them as a nested bullet list, one item per line, never a semicolon run-on. Three or more parallel items are a checklist; write one.

### The anchor rule — locations must tell the truth

The lint is mechanical, at write time, against the step-3 parsed changed ranges — and it is **section-dependent**:

- under **Problems** and **Observations**, a located heading's start line **must fall inside a changed range** of the canonical diff for its file — GitHub can host an inline comment only there. (GitHub sometimes accepts a comment whose range merely _ends_ in the diff, but that produces misplaced comments and is hard to get right — assume it does not.)
- under **Pre-existing**, the start line **must not** fall in any changed range: in a changed range it would be caused or mirrored by the PR, which is the definition of not-pre-existing.

A heading that fails its section's check is never written as-is — its finding is re-routed. Findings whose defective line is not in the diff still get located under Problems/Observations — by causality. **Check the precondition mechanically first**: a defect whose own start line falls in a step-3 changed range is located at the defect, always — the routes below are fallbacks for defects the diff cannot host, never alternatives to a direct location.

- **Caused by the change, defect outside it** (the loop body was optimized and the exit condition above it is now wrong; a parameter list changed and the docblock went stale): locate at the **causing hunk**, name the affected line in the prose with a permalink, and open causally — "here the route becomes …, so … at \<permalink\> now …". Lead-with-cause then arrives by structure, not by discipline.
- **The PR fixes one instance and an identical twin survives elsewhere**: locate at the **fixed instance** — "the same defect survives at \<permalink\>" — framed as consistency cleanup, not as a fault of this PR.
- **No causing hunk and no mirrored fix**: pre-existing by definition → its block goes under the third section (`Pre-existing`), located at the defect itself — where its own lint requires the line to sit _outside_ the ranges.

One bucket, one test — for defect lines the ranges exclude: _is there a changed range that causes or mirrors it?_ Yes → locate there, under Problems/Observations. No → Pre-existing, located at the defect.

### The one test — located vs locationless

- **Cross-cutting**: the locus is a property of the whole change ("mutates the records without a transaction, unlike the rest of the codebase") — no single line is "the" finding → a **locationless block**: heading with no link, one paragraph of prose. The posting step folds the checked ones into the PR-level comment.
- **Repeated**: N independent instances of the same defect (the wrong hydration mode in five places, a copy-pasted typo) → **N separate located blocks**, one per instance — never one comment with "applies to the others too…".

The test: _is there a single line that IS the finding?_ Yes → located (one block per instance). No → locationless.

### Classification and order

Sort `###` blocks under the three `##` headings, always all three and always in this order — **Problems**, **Observations**, **Pre-existing** — written with the glossary's `sections` values for the PR's language (English `## Problems` / `## Observations` / `## Pre-existing`; Italian `## Problemi` / `## Osservazioni` / `## Preesistenti`). Within each, decreasing priority — **order is the only priority signal**.

- **Problems** — everything _objectively wrong_, whatever its size: bugs, correctness errors, reuse/SSOT violations, standard/rule/style deviations, typos, dead code, stale comments or symbols, missing required headers, user-facing defects like wrong translations. The test for inclusion is **one correct resolution**, not severity — a typo is a small problem, but it _is_ a problem.
- **Observations** — genuine _decisions_ only: a scoping choice (here or in a follow-up?), a design trade-off with real alternatives, a point where the codebase is itself inconsistent so no rule clearly applies. A finding with one correct fix is a Problem, however minor, and does not belong here.
- **Pre-existing** — defects in untouched files, and the residue in touched files that no hunk causes or mirrors. Located at the defect itself (its lint requires the line _outside_ the changed ranges), validated like everything else, never in the status table, and last because by definition the floor of the priority order.
- **Classify by defect-vs-decision, never big-vs-small.** Default a finding to Problems; move it only when it is a genuine open choice. Sloppiness is a defect like any other — typos, dead code, duplicated intent, a stray blank line, a mistranslation all spread by imitation if left unfixed.
- **Never label severity or kind** (in any language): no "minor", "nit", "non-blocking", "cosmetic", "trivial", no separate "nits" group (bucketing the small ones is itself a soft "lesser" label), no "bug"/"standards" kind-tags — the wording already conveys what sort of thing it is. A reader who sees "minor" files it under "who cares" and stops; order tells them where to start without licensing them to stop.
- **All three headings are always written, in order, even when a section is empty.** The section identity is positional — the posting step reads the 1st/2nd/3rd `##` as Problems/Observations/Pre-existing regardless of the label text — so omitting an empty section would shift the ones below it and misroute their findings. An empty section is just a heading with no blocks: it posts nothing, the verdict already says the result is clean, and it costs one line. (For the same reason the human should relabel headings, never delete them.)

### Register — default `junior`, optional `expert`

The command's one optional argument selects it: nothing or `junior` → `junior`; `expert` → `expert`. Register is **presentation only** — the findings, their defect-vs-decision classification, completeness, priority order, the no-severity-labels rule, location, and the second-person address are identical in both. It never drops, softens, reclassifies, or reorders a finding; it changes only how each one is explained. The instinct throughout is _assume intelligence, not knowledge_: explain the concept, never the reader's competence.

- **`junior` (default).** Write for a sharp reader who may not have met the concept yet. Name and briefly define any jargon, pattern, or acronym in place, once. For each problem add a plain _why_ — why the current code bites and why the fix resolves it — in short sentences, one idea each. (This is the one place the register explains beyond the finding itself, and it explains the _concept behind the problem_, still never the author's change back to them.) Plain prose reads shorter than dense prose, so this is also what keeps a long review from feeling verbose.
- **`expert`.** Write for a peer who already shares the domain vocabulary. Use the terms directly without defining them; state the problem and the fix and trust them to infer the mechanism. Terser, no concept-teaching — but every finding still present, in the same order, at the same location.

Both registers: address the author in the second person ("the component still reads it from the query…", "you'll want to…") — this is feedback left _for the person who wrote the PR_, not a report about them. Encouraging and respectful, never judgemental or patronising; credit what works; frame each problem as what will bite and how to fix it, not as a failing; skip verdict-language ("wrong", "bad") and every shade of condescension ("as you know", "obviously", "as you surely know"). Warmth never softens substance — state every problem plainly and completely; hedging or burying a real issue helps no one, and clarity is itself a courtesy. The author should finish the review wanting to act on it, not defending against it.

### Rendering on GitHub — format consequences

- Do not hard-wrap. Every paragraph, list item, and table cell is one unbroken line, however long; GitHub turns a lone newline into a `<br>`. Blank lines only between blocks. (The fix-on-its-own-line rule is a block boundary, not a hard wrap: a blank line precedes it.)
- Permalinks: a Markdown link whose visible text is the path and line range (`user-cms-detail.component.ts L52`) and whose target is `https://github.com/<owner>/<repo>/blob/<sha>/<path>#L<start>[-L<end>]` — here the `L` is correct; GitHub's fragment grammar is not VS Code's. `<owner>/<repo>` is frontmatter `repo`; `<sha>` is frontmatter `head`, which the precondition guarantees is also the PR head on GitHub — so every permalink is exact and live the moment it is written. Pin to the SHA, never to a branch — GitHub keeps PR head commits, so the link survives the merge.
- Language conventions bind your prose too (step 4's rule set, plus your own command of the target language): grammatical gender and declension of domain terms (whether "PR" or "issue" takes a masculine or feminine article in the target language, and so on), terminology, tone.

### Worked example

Illustrative shape — **write in the PR's actual language**, using its glossary for the section headings, the status faux-heading, and the table's outcomes and headers; this example happens to be an English PR, so it uses the `en` glossary. `owner/repo` and `<sha>` come from the snapshot (pr.json's url; state.json's head). The PR here moved a user-CMS page to its own route and claims "Fixes #839".

```markdown
---
pr: 142
repo: owner/repo
head: <sha-of-local-HEAD>
base: <sha-of-base>
runs: 1
---

The bulk of the work is solid and well aligned with the conventions; the snag is the detail page, which no longer opens after the route move. Two translations are still missing, plus a little polish.

**Status:**

| Requirement / Declared change | Outcome | Note |
| --- | --- | --- |
| R1 — Feature parity with the WP view | ⚠️ Partial | List is complete; the detail page is unreachable, see app-routing.module.ts L34 |
| Rename `WpUserList` → `UserCmsList` (declared in the text) | ✅ OK | Consistent everywhere, tests included |

Changes present in the diff but declared nowhere — neither in a linked issue nor in the PR text; for alignment, not as faults:

- Updated `karma.conf.js` to the new coverage-report path.

## Problems

### [ ] 1 1 [app-routing.module.ts L34](./projects/example/src/app/app-routing.module.ts#34)

The route becomes `user-cms/:id`, so the id now travels in the _path_ (the `/123` segment of the URL), no longer in the _query string_ (a would-be `?id=123`). The component still reads it from the query ([user-cms-detail.component.ts L52](https://github.com/owner/repo/blob/<sha>/projects/example/src/app/user-cms/user-cms-detail.component.ts#L52)): on `/user-cms/123` the query holds no `id`, so `id` stays `0` and the "missing id" guard fires.

Read the path param with `paramMap.get('id')`.

### [ ] 1 6 [messages.en.xlf L198](./projects/example/src/i18n/messages.en.xlf#198)

The key `userCms.detail.title` is born here and in `it` and `de`, but not in the other locales, which fall back to English. Add the missing translations:

- `fr` — "Détail utilisateur"
- `es` — "Detalle de usuario"

### [ ] 1 6 [messages.de.xlf L210](./projects/example/src/i18n/messages.de.xlf#210)

Typo in the just-added German translation.

"Benutezr-Detail" → "Benutzer-Detail".

### [ ] 1 3 [_material3.scss L1](./projects/example/src/styles/_material3.scss#1)

Stray leading blank line.

Remove it.

## Observations

### [ ] 1 5

The PR says "Fixes #839", but the detail page still depends on `WpToolsLocalApiService` — the very dependency #839 asks you to reduce. Bring that into this PR, or open a follow-up? Either is fine; if you go with the follow-up, it's worth dropping the "Fixes" so the issue stays open.

### [ ] 1 3 [app-routing.module.ts L36](./projects/example/src/app/app-routing.module.ts#36)

The redirect from the old `wp-tools/user-cms` keeps bookmarks and external links alive, but it's also one more route to maintain. Keep it for a release and then drop it, or remove it now? Both are fine; it's just worth choosing deliberately and leaving a comment with the choice.

## Pre-existing

### [ ] 1 1 [date-utils.ts L23](./projects/example/src/app/shared/date-utils.ts#23)

The comment promises UTC but `formatDay` uses local time; no hunk in this PR touches or mirrors it — it surfaced while reading the callers.

Either `formatDay` switches to the `getUTC*` counterparts, or the comment stops promising UTC — depending on which of the two is the contract the callers expect.
```

Note what the example pins:

- **Every checkbox is unchecked** — the machine never checks one; posting waits for the human's `[x]`.
- **The marquee finding locates at its cause.** The defective read at `user-cms-detail.component.ts` L52 is _outside_ the diff — the PR changed the route, not that line — so the location is the causing hunk (L34 of the routing module), the prose opens with the cause ("the route becomes…"), the affected line rides along as a permalink, and the fix is the last line. The anchor rule doing the lead-with-cause work by itself.
- **Missing things locate where they should have been born.** The absent `fr`/`es` translations have no line of their own; the causing hunk is the key's introduction, and the parallel languages are a checklist under one heading — one locus, one finding.
- **The `de` typo is its own block**, not a bullet under the translations finding: an independent defect with its own line, and independent instances never share a comment. Both findings carry agent 6 — same lane, different locations, distinct identities.
- **The smallest Problem keeps the full shape** — statement, blank line, fix — with no "minor" tag and no quarantine: it ranks last by position alone.
- **The Pre-existing fix carries no preamble.** The section heading classifies; the fix line is pure remedy, ready to be pasted into an issue unedited.
- **The #839 question is the locationless block**: no single line _is_ the dependency on `WpToolsLocalApiService`, so its heading ends at the agent number, and when checked it travels to the PR-level comment, not inline. The pre-existing UTC comment sits under the third section (`Pre-existing`), located at the defect itself — a line no changed range contains, exactly as that section's lint demands — and closes with a fix paragraph written to be lifted into an issue.
- **The status table cross-references by location link text** ("see app-routing.module.ts L34"), plain and unlinked — never by run or agent numbers.

This example is in the default `junior` register: the route finding glosses _path_ vs _query string_ in place and walks the mechanism (`id` stays `0`, the guard fires) rather than assuming it. The **same block in `expert`** keeps the identical heading and shape and drops the teaching — "The id is a path param now, but [user-cms-detail.component.ts L52](…) still reads it from the query string: it stays `0`." / "Use `paramMap.get('id')`." — same finding, same cause-first opening, same final-line fix; only the explanation flexes.

## Additive re-runs — the merge

Within one preparation, re-running the review **stacks onto** `REVIEW.md` instead of overwriting it. Two invariants make this sound: the precondition's hard gate (tree == snapshot) means line numbers never move between runs, so **agent + location is a stable identity** for a located finding within a preparation; and **only checked blocks post**, so anything the merge gets wrong is inert until a human endorses it. The generation boundary stays clean — a new preparation requires deleting `REVIEW.md` first, and re-prepping wipes `.pr-review/` with it.

The merge is one rule. For each finding in the run document: if a block with the same identity already exists in the curated file — checked or unchecked, wherever the human moved it, however they edited it — **skip it**, leaving the existing block untouched; otherwise **insert it, unchecked**, in its section at its priority position among the existing blocks (order is the only priority signal, so the position is a judgment made among the human's kept blocks too; recreate a missing `##` heading in the file's language, in the canonical order). Locationless findings have no machine-checkable identity and are **always inserted** — deduping them is the human's job, and the duplicates arrive unchecked, so the cost is reading, never posting.

The machine never checks, unchecks, edits, or deletes an existing block, and never merges the body: the curated verdict and Stato stay verbatim; the run's fresh body is simply dropped. Frontmatter: bump `runs` by one — to exactly the run number fixed in the precondition, the one this run's files and inserted headings already carry — so the highest run number in the file marks what the last merge added. Blocks the new run did not reproduce stay where they are: runs are noisy; absence from run _n_ invalidates nothing.

Curation, stated once for the human's benefit: **leave unwanted findings unchecked rather than deleting them**. Deleting is allowed but does not persist — a later run can legitimately reinsert the finding, unchecked. After a merge, say in the session what was inserted; the run numbers in the file already say the rest.

## Operating notes

### False positives

False positives to exclude throughout (do NOT flag):

- Things that look like a bug but are correct in context.
- Subjective preferences with no rule or standard behind them — pure taste a senior engineer would not raise. This never downgrades an _objective_ small defect: a typo, dead code, or a stale comment is a Problem, not a nitpick.
- A new type or component that only shares a _shape_ with an existing one but means something different (a timestamp range vs a date range) — same structure is not duplication.
- Issues a linter / static analyzer (PHPStan, ESLint, …) already catches.
- A project rule explicitly silenced in the code (e.g. a suppression comment).

Pre-existing issues are **not** false positives — they are routed, not discarded: no causing hunk and no mirrored fix → a located block under the third section (`Pre-existing`); an identical instance of something this PR fixes → a real finding, located at the fixed instance as consistency cleanup. Found incidentally while reviewing, never hunted.

### `REVIEW.md` and the working tree

`REVIEW.md` is hidden from `git status` by the **preparation**, which maintains a three-entry list in `.git/info/exclude` (`.pr-review/`, `.pr-review-run/`, `REVIEW.md`) — deliberately not `.gitignore`, which is tracked: an entry there would itself dirty the tree and commit one reviewer's tooling into the project's history. The file can neither be committed by accident nor make the next preparation refuse the tree as dirty. Its absence from `.gitignore` is the **correct** state: do not check for it, do not recommend adding it, and do not report on the file's ignore status at all — that invariant is the script's, enforced before this skill runs. Note that `.git/info/exclude` is not visible to you (protected path) — trust it.

### No posting on GitHub

**Do not post anything to GitHub.** The output is the local file only. Posting the curated file is a separate, human-gated tool — **`pr-finalize`** — run from a shell after curation; this skill never posts. (`pr-finalize` reads the same `.pr-review/` snapshot, posts one review object, and leaves a `posted.md` marker that closes the preparation.)

### See also

`pr-review <id> [register]` — a self-contained shell script, run from the repo root outside any Claude session — prepares the branch (checkout, rebase, terminal-confirmed force-push), captures the GitHub snapshot this review reads, and launches a sandboxed interactive `claude` session with this review as its initial prompt. That script is the normal entry point: preparation needs network and `.git/config` writes (unsandboxed), the review needs neither (sandboxed, zero egress), and the script is that boundary. `pr-review prepare <id>` prepares without launching, for inspecting the tree first. Use `/pr-review:run` directly from an already-open session when the `pr/<id>` branch is prepared and you want to review — or re-review — without fetching again.

`pr-finalize` — a self-contained Python tool, also run from the repo root outside any session — posts the curated `REVIEW.md` to GitHub as one review object (checked located findings inline, the rest folded into the body under their section labels), then marks the preparation finalized. The review's verdict follows from curation: **no checked finding approves the PR; any checked finding — in any section — requests changes** (the checkbox is the blocking signal, not the section). Before prompting it prints a per-section recap (checked / unchecked / total) and the pending verdict; an approval takes a second confirmation, since an unmodified `REVIEW.md` may be unread rather than clean. It takes no arguments — the PR comes from the same `.pr-review/state.json` snapshot — and `--dry-run` prints the payload without posting. It needs the network and `gh`; it builds the request with the standard library, so unlike the review path it needs no extra runtime beyond `python3` and `gh`.
