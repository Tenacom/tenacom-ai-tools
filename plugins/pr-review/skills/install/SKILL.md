---
name: install
description: Put the `pr-review` and `pr-finalize` commands on your PATH after installing this plugin. Run from a terminal with `claude -p /pr-review:install`, and again after each plugin update to refresh the links.
allowed-tools: Bash(pr-install), Bash(pr-install:*)
disable-model-invocation: true
---

Run the bundled `pr-install` command exactly once, then report the result. Do not pass arguments, do not run anything else, and do not edit any files yourself.

`pr-install` ships in this plugin's `bin/` directory, so it is already on your PATH inside this session — invoke it as a bare command:

```bash
pr-install
```

It puts the commands on the user's PATH as symlinks in `~/.local/bin`, backed by copies it keeps under `~/.local/share/pr-review/bin`. Three are the end-user commands, `pr-review`, `pr-finalize` and `pr-check`; the fourth, `pr-assemble-rules`, is an internal helper that `pr-review` calls during preparation, linked alongside so `pr-review` can find it. It is idempotent — run after a plugin update it refreshes those copies, and otherwise it does nothing.

When it finishes, tell the user whether `pr-review`, `pr-finalize` and `pr-check` are now available (the helper need not be mentioned), and — if `pr-install` printed a note that `~/.local/bin` is not on their PATH — pass that note along verbatim, since they will need to fix their PATH before the commands work in a shell.
