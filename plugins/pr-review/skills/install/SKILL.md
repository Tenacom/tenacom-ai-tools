---
name: install
description: Put the `pr-review` and `pr-finalize` commands on your PATH after installing this plugin. Run from a terminal with `claude -p /pr-review:install`, and again after each plugin update to refresh the links.
allowed-tools: Bash(install-shims), Bash(install-shims:*)
disable-model-invocation: true
---

Run the bundled `install-shims` command exactly once, then report the result. Do not pass arguments, do not run anything else, and do not edit any files yourself.

`install-shims` ships in this plugin's `bin/` directory, so it is already on your PATH inside this session — invoke it as a bare command:

```bash
install-shims
```

It puts the commands on the user's PATH as symlinks in `~/.local/bin`, backed by copies it keeps under `~/.local/share/pr-review/bin`. Two are the end-user commands, `pr-review` and `pr-finalize`; the third, `pr-assemble-rules`, is an internal helper that `pr-review` calls during preparation, linked alongside so `pr-review` can find it. It is idempotent — on a session after a plugin update it refreshes those copies, and otherwise it does nothing.

When it finishes, tell the user whether `pr-review` and `pr-finalize` are now available (the helper need not be mentioned), and — if `install-shims` printed a note that `~/.local/bin` is not on their PATH — pass that note along verbatim, since they will need to fix their PATH before the commands work in a shell.
