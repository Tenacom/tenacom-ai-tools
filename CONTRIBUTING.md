# Contributing

Thanks for your interest in improving Tenacom AI Tools. This repository is a
[Claude Code](https://claude.com/claude-code) plugin marketplace: the [README](README.md)
covers installing and using the plugins, and this guide is for working on them.

The conventions that govern the repository live in [`.claude/rules/`](.claude/rules/). They
double as Claude Code's project instructions, so they are authoritative and kept current;
this guide is a human-facing entry point that links into them, and where the two differ, the
rules files win.

## Getting set up

You will need [Git](https://git-scm.com/), the `claude` CLI (to install and test the
plugins), Python 3 with the `python3-venv` package on Debian/Ubuntu, and `make`.

The repository uses a fork-and-branch workflow:

1. Fork `Tenacom/tenacom-ai-tools` on GitHub and clone your fork.
2. Create a topic branch off `develop` — see [How work flows](#how-work-flows).
3. Build the developer tooling once with `make tools`. This creates a local `.venv` holding
   the pinned ruff and pyright from [`requirements-dev.txt`](requirements-dev.txt).

## Before you push

Run the quality gate over the repository's Python:

```bash
make check
```

That runs `make lint` (ruff) and `make typecheck` (pyright) over every plugin's Python
sources, and both must pass. The tool postures, and the reasoning behind them, are in
[`.claude/rules/python-tooling.md`](.claude/rules/python-tooling.md).

## How work flows

`main` is the branch the marketplace is served from, so it must stay releasable at all
times; everyday work targets `develop` instead. Branch off `develop`, and open your pull
request against the `develop` branch of `Tenacom/tenacom-ai-tools` — GitHub preselects
`main`, so switch the base yourself. The full branching and release model, with the reasons
for each choice, is in
[`.claude/rules/versioning-and-releases.md`](.claude/rules/versioning-and-releases.md).

Plugins are versioned individually, and bumping a plugin's `version` is the release gate.
Do not bump it in a feature branch; that happens only when a release is cut.

## Changelog

Record user-visible changes in the affected plugin's `CHANGELOG.md`, under its
`## Unreleased changes` section. Catalog-level events — a plugin added, renamed, or removed —
go in the root [`CHANGELOG.md`](CHANGELOG.md) instead. How to word an entry, and the house
section names to use, are in
[`.claude/rules/changelog-entries.md`](.claude/rules/changelog-entries.md).

## Style

File formatting is set by [`.editorconfig`](.editorconfig) and, for Markdown, the
[markdownlint configuration](.markdownlint-cli2.jsonc); the finer points that neither can
express are in [`.claude/rules/file-formats.md`](.claude/rules/file-formats.md). Per-plugin
development notes — the invariants a change must respect — live under
[`.claude/rules/plugins/`](.claude/rules/plugins/); read the one for the plugin you are
touching before you start.

## License

By contributing, you agree that your contributions are licensed under the repository's
[MIT license](LICENSE).
