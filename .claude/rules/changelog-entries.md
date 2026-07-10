# Writing changelog entries

The two-file changelog layout (per-plugin vs root) and its versioning mechanics live in
[versioning-and-releases.md](versioning-and-releases.md). This file is about the prose inside
an entry.

## State what changed — nothing else

An entry states **what changed**: not how, not why at length, and not what was there before.
It is a changelog entry, not a blog entry. Deep rationale belongs in the spec, the rules
files, or the commit message; readers scan a changelog for impact, and every sentence that is
not the change itself dilutes it.

- **Lead with the user-visible change in one bold sentence.** Explanation, if any, follows in
  its own short sentences.
- **A one-line, value-level justification is fine** ("that was curation work for no value");
  a history of the design that led here is not.
- **Write for the user of the plugin**, in terms of what they see and do — never in terms of
  internal components or spec vocabulary a user cannot be expected to know.
- **No motivational or praise-shaped prose.** Programmers read it as filler at best.
- **Mark breaking changes with a leading `**BREAKING:**`** — reserved for changes that break
  the _consumer's_ interface or workflow (arguments, file formats they write, commands),
  not for mere changes in produced output.

## Section names

Per-plugin changelogs follow the Keep a Changelog structure with house section names — `New
features`, `Changes to existing features`, `Bugs fixed in this release`, `Known problems
introduced by this release` — not the stock `Added`/`Changed`/`Fixed`. Keep them verbatim,
and keep the empty sections under `Unreleased changes` in place as slots for future entries.

The root changelog carries no per-type sections at all: one dated `##` heading per event,
plain bullets under it ("Updated `pr-review` to version 2.0.0"), with all detail delegated
to the plugin's own changelog.
