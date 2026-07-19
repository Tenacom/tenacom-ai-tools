# Python tooling

The repo's Python lives in `plugins/pr-review/bin/`. Two tools gate it — **ruff**
(lint) and **pyright** (type check) — wired through a root `Makefile` that fans out to
per-plugin `plugin.mk` files: `make lint`, `make typecheck`, `make check`.

Run `make tools` once first: it builds a `.venv` with the versions pinned in
`requirements-dev.txt` (needs the `python3-venv` package on Debian/Ubuntu). Pinning is
deliberate — a ruff upgrade can change which rules fire under `select = ["ALL"]`, so the
version is part of the gate, not a floating dependency. To use tools already on PATH
instead, override: `make check RUFF=ruff PYRIGHT=pyright`. The Ruff and Pylance editor
extensions read `ruff.toml` / `pyrightconfig.json` directly, so in-editor diagnostics
work without the venv.

## CI is where the gate is enforced

`.github/workflows/check-python.yml` runs `make tools` then `make lint` and `make
typecheck` on every pull request and on every push to `main` or `develop`. It is not
redundant with a local run: the pins fix _which_ rules exist, not which ones _fire_.
Ruff's `EXE` family is platform-conditional — "not enforced on Windows or WSL", in ruff's
own words, since those filesystems carry no meaningful execute bit — so a WSL checkout
passes `make check` over a shebang'd non-executable file while CI fails it. That is how
`pr_review_cleanup.py`'s vestigial shebang survived until the workflow landed. A local
pass is necessary; CI is the authority.

The two tools are separate steps, so a ruff failure does not hide the pyright errors.
Both annotate the changed lines: ruff through `RUFF_OUTPUT_FORMAT=github` (a ruff
environment variable, so the Makefile needs no knob), pyright through a committed problem
matcher at `.github/problem-matchers/pyright.json`, because pyright has no GitHub output
format of its own. The matcher's pattern tracks pyright's plain output — check it against
a real run if a pyright bump ever changes that format.

## The file list is explicit, not discovered

The `pr-*` command scripts are extensionless (they run as bare commands). **Neither ruff
nor pyright analyzes an extensionless file during directory discovery — only when it is
named explicitly.** So the sources are enumerated in each plugin's `plugin.mk`
(`PY_SOURCES += …`), never left to an `include` glob or a bare `ruff .`. A new plugin
adds its own `plugin.mk` and one `include` line in the root `Makefile`.

The consequence for the editor: Pylance analyzes an open `pr-*` script via its `#!`
shebang and applies `pyrightconfig.json` anyway, but a whole-tree or CI run has to go
through the Makefile to reach them.

## pyright — strict minus the Unknown-type family

`pyrightconfig.json` sets `typeCheckingMode: "strict"` but turns the `reportUnknown*`
rules off. Those fire because `json.loads` returns `Any` and it spreads; silencing them
honestly would mean casting every JSON boundary — ceremony these stdlib scripts do not
earn. Everything else strict checks stays on. `extraPaths` points at the bin dir so the
sibling `pr_review_*` imports resolve; without it pyright cannot see `die` /
`bail_on_problems` as `NoReturn` and invents a cascade of possibly-unbound and
missing-return errors that vanish once the imports are found.

## ruff — everything, then pared back

`ruff.toml` selects `ALL` and removes rules one at a time, each with a reason, so a ruff
upgrade surfaces new rules instead of leaving them silently off. Removals are scoped to
what genuinely does not fit CLI scripts (`print` as output, `git`/`gh` subprocess calls,
package-layout rules) — see the file's own comments.
