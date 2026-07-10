# Versioning and releases

How this marketplace and its plugins are versioned, served, and released, and the reasoning behind each choice.
The mechanics below are grounded in the official docs: <https://code.claude.com/docs/en/plugin-marketplaces>.
When in doubt about update behavior, re-read the "Version resolution and release channels" section there rather than guessing.

## The marketplace is rolling, served from `main`

- The marketplace itself is **not** versioned. It is an index (a catalog), and Claude Code has no consumer-side mechanism to select a marketplace version: `/plugin marketplace update` always pulls the served branch's HEAD. A version number would gate nothing, so it would be pure bookkeeping that can drift from the plugin versions it sits next to.
- The repository default branch is `main`, so a bare `/plugin marketplace add <owner>/<repo>` resolves to `main`. No `ref` ceremony for consumers.
- Catalog-level history (a plugin added, updated to a new version, renamed, deprecated, or removed) may be narrated in a root `CHANGELOG.md` **without** a version number. Version updates aside, those are exactly the events that touch shared root files, so the changelog and the conflict surface nearly coincide.

## Plugins are versioned

- Each plugin carries a semver `version` in its own `plugin.json`. **Do not** also set `version` in the plugin's marketplace entry: when both exist, `plugin.json` wins silently and a stale manifest can mask the marketplace value. One home only.
- Bumping `version` **is** the release gate (see below). Bump it on every release; never bump it while the plugin is mid-change.
- Plugin sources stay as local paths (`./plugins/<name>`), which is safe because we only ever serve `main`.
- Per-plugin docs and changelogs live in the plugin's own subtree. Namespaced tags (`<plugin>/X.Y.Z`) are welcome as immutable anchors, but they are decorative: nothing resolves against them, so they cannot contradict the `version` field.

## How updates resolve (and why `main` must stay coherent)

Claude Code resolves a plugin's version from the first of: `version` in `plugin.json`, then `version` in the marketplace entry, then the source's git commit SHA. That resolved version determines both the cache path and update detection. Two consequences drive every rule above:

- **Setting `version` pins the plugin.** Pushing commits without bumping the field does nothing for users who already have that version — Claude Code sees the same version and keeps its cached copy. This is what makes discrete releases possible, and it means unfinished work on the served branch is invisible to existing users until you bump.
- **A new install copies the served branch's HEAD and labels it with the declared version.** So if `main` ever carries an unfinished plugin state while its `version` still reads the last release, a fresh install gets broken files stamped as a released version. Therefore **`main` must always be coherent and releasable** — this is a hard correctness requirement, not etiquette. (Omitting `version` instead makes every commit its own version, i.e. true rolling; we deliberately do not do that for shipped plugins.)

## Branching and releases

- `main` is the served branch and the repository's git default branch, so a bare `/plugin marketplace add <owner>/<repo>` resolves to it and GitHub pre-selects it as a PR base. Protect it: require pull requests and review, and block direct pushes and force-pushes. It must stay coherent and releasable at all times (see above).
- `develop` is the normal PR base: everyday work targets `develop`, where changes are assembled and smoke-tested, then promoted to `main` when releasable. Because `main` is the git default, GitHub offers it as the PR base by default, so you switch the base to `develop` yourself — a PR accidentally left targeting `main` is a private, reversible mistake a reviewer catches before merge. That is a far safer failure mode than making `develop` the git default, which would force consumers to type a non-default `add` command. That trade-off is why `main` stays the git default even though `develop` is where PRs normally land. Resetting `develop` to `main` immediately after a release is standard practice.
- Spin up per-plugin `develop/<plugin>` branches only when two plugins are worked on in parallel and their staging cadences must decouple. Base them on `main`, promote independently, and delete them afterward — they are short-lived by design, so they need no reset ritual.
- We use rebase & merge. That rewrites commit SHAs on promotion, which is why long-lived staging branches are reset or recreated rather than promoted repeatedly.

## Organizing shared files

Anything at the repository root that several plugins touch is a shared conflict surface under rebase & merge. Keep that surface small and compartmentalized so changes rarely overlap:

- `marketplace.json` already isolates each plugin in its own entry — keep it that way.
- For documentation, prefer pushing substance into per-plugin subtrees (e.g. a thin root `README.md` that links out to each plugin's own `README.md`). This is a **preference, not a strict rule**: separate per-plugin sections within a single Markdown document are perfectly fine. Because we never rebase one plugin's staging branch onto another's, only one section tends to change at a time, so conflicts stay rare and trivial to resolve regardless.

## Changelogs

All changelogs follow the [Keep a Changelog](https://keepachangelog.com) style and are **hand-maintained**. We do not use Conventional Commits, so commit-driven generators (release-please, git-cliff) are out; there is nothing to automate, and nothing to migrate later. The changelog layout mirrors the versioning split — one layer per version model. How to write the entries themselves — and the house section names the real files use — is [changelog-entries.md](changelog-entries.md).

- **Per-plugin `CHANGELOG.md`** (in `plugins/<name>/`) carries the substance: one section per release, versioned and dated, its heading linking to the `<plugin>/X.Y.Z` release tag. Keep a `## Unreleased changes` section at the top (with the four house sections as empty slots, see [changelog-entries.md](changelog-entries.md)) in the normal way, since these files are gated by version bumps.

  ```markdown
  ## Unreleased changes

  ### New features

  ### Changes to existing features

  ### Bugs fixed in this release

  ### Known problems introduced by this release

  ## [1.1.0](https://github.com/Tenacom/tenacom-ai-tools/releases/tag/pr-review/1.1.0) (2026-07-15)

  ### New features

  - **`pr-finalize` now posts inline comments.**
    Checked findings pinned to changed lines post at those lines instead of folding into the review body.
  ```

- **Root `CHANGELOG.md`** narrates catalog-level events only (a plugin added, updated to a new version, renamed, deprecated, removed). It is **version-less but dated**: the marketplace is rolling, so there are no versions or tags to anchor sections — the date is the anchor. It never mirrors plugin tags; per-version sections belong exclusively to the per-plugin files. Name the affected plugin in each entry (and its version where relevant). Because a catalog event is live the moment it lands on `main`, the root file needs **no unreleased section** — append a dated entry when the change merges. It carries no per-type subsections either: plain bullets under the date.

  ```markdown
  ## 2026-06-29

  - First marketplace release. The only released plugin is `pr-review`.
  ```

This two-file split is what keeps changelogs free of cross-plugin aggregation: each plugin's history stands alone, and the root file is sparse hand-written narration of the same events that touch the shared root surface.
