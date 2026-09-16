# Claude Code skills brief agent

This agent finds notable Claude Code skills and plugins, researches the strongest results, and produces a short briefing.

## How it works

1. Plans a small set of search queries.
2. Searches GitHub and Hacker News.
3. Reads the top repositories and pages for more context.
4. Uses a Databricks-hosted language model to write the brief.

## Run it

```bash
git clone https://github.com/adamgurary/claude-skills-brief-agent.git
cd claude-skills-brief-agent
bash setup.sh
```

`setup.sh` installs the required tools, resolves and verifies the newest stable
MLflow release from the configured package index, opens a browser for Databricks
login, and runs the agent once. Re-running setup automatically upgrades MLflow
when a newer stable release is available.

For later runs:

```bash
.venv/bin/python plain/run.py
```

Generated Markdown and HTML briefs are saved in `output/`.
