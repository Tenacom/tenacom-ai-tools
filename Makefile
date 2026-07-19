# Repository developer tasks, aggregated across all plugins.
#
# Each plugin ships a plugin.mk that appends its Python sources to PY_SOURCES;
# the targets below run the tools once, from the repo root, over the combined
# list. Adding a plugin is one more `include`. The lists are explicit rather
# than a glob because the pr-* command scripts are extensionless, and neither
# ruff nor pyright discovers an extensionless file by walking the tree — it must
# be named. See .claude/rules/python-tooling.md for the full rationale.
#
# ruff and pyright come from a local virtualenv with pinned versions; run
# `make tools` once to build it (needs the python3-venv package on Debian). To
# use tools already on your PATH instead, override:
#   make check RUFF=ruff PYRIGHT=pyright

RUFF    ?= .venv/bin/ruff
PYRIGHT ?= .venv/bin/pyright

PY_SOURCES :=

include plugins/pr-review/plugin.mk

.PHONY: check lint typecheck tools
check: lint typecheck

lint:
	$(RUFF) check $(PY_SOURCES)

typecheck:
	$(PYRIGHT) $(PY_SOURCES)

# One-time setup (re-run after bumping requirements-dev.txt).
tools:
	python3 -m venv .venv
	.venv/bin/pip install -r requirements-dev.txt
