---
name: install
description: Put the `pr-review` and `pr-finalize` commands on your PATH after installing this plugin. Run once from a terminal with `claude -p /pr-review:install`; a SessionStart hook keeps the links current thereafter.
allowed-tools: Bash(install-shims), Bash(install-shims:*)
disable-model-invocation: true
---

Run the bundled `install-shims` command exactly once, then report the result. Do not pass arguments, do not run anything else, and do not edit any files yourself.

`install-shims` ships in this plugin's `bin/` directory, so it is already on your PATH inside this session — invoke it as a bare command:

```bash
install-shims
```

It puts `pr-review` and `pr-finalize` on the user's PATH: two symlinks in `~/.local/bin`, backed by copies it keeps under `~/.local/share/pr-review/bin`. It is idempotent — on a session after a plugin update it refreshes those copies, and otherwise it does nothing.

When it finishes, tell the user whether the two commands are now available, and — if `install-shims` printed a note that `~/.local/bin` is not on their PATH — pass that note along verbatim, since they will need to fix their PATH before the commands work in a shell.
