# pr-review plugin — Python sources for the repo-root lint / typecheck targets.
#
# The pr-* command scripts are extensionless (invoked as bare commands), so ruff
# and pyright will not pick them up by directory discovery; they are listed
# explicitly. The pr_review_*.py modules are imported, never run.

PY_SOURCES += \
	plugins/pr-review/bin/pr-finalize \
	plugins/pr-review/bin/pr-check \
	plugins/pr-review/bin/pr-cleanup \
	plugins/pr-review/bin/pr-assemble-rules \
	plugins/pr-review/bin/pr_review_lint.py \
	plugins/pr-review/bin/pr_review_cleanup.py \
	plugins/pr-review/bin/pr_review_common.py
