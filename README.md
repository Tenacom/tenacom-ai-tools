# Tenacom AI Tools

A [Claude Code](https://claude.com/claude-code) plugin marketplace for Tenacom's AI tooling.

![Repobeats analytics image](https://repobeats.axiom.co/api/embed/1dd84c7381e50359eb0091f1c56eaee3525892b7.svg "Repobeats analytics image")

## Adding the marketplace

Register this repository as a Claude Code plugin marketplace — a one-time step per machine:

```bash
claude plugin marketplace add Tenacom/tenacom-ai-tools
```

Once it is added, plugins can normally be installed with `claude plugin install <name>@tenacom-ai-tools`. Each plugin may require additional installation steps — see the plugin's README.

## Plugins

### pr-review

A complete system for AI-assisted GitHub pull request reviews — a sandboxed, six-agent parallel review that reads the PR against the full local source and writes a curatable `REVIEW.md`, which you then post to GitHub as a single review object.

```bash
claude plugin install pr-review@tenacom-ai-tools
```

Then follow the [pr-review README](plugins/pr-review/README.md) to put its `pr-review` and `pr-finalize` commands on your `PATH` (a one-time setup step); that README also covers requirements, usage, and language support.

## Requirements

The **`claude`** Claude Code CLI is needed to add the marketplace and install plugins. Each plugin may have its own additional requirements — see the plugin's README.

## License

[MIT](LICENSE) © Tenacom and contributors.
