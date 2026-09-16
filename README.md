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

## Model endpoint

The agent uses `databricks-qwen3-next-80b-a3b-instruct` by default. Set
`BRIEF_AGENT_MODEL_ENDPOINT` to use a different Databricks-hosted model endpoint:

```bash
BRIEF_AGENT_MODEL_ENDPOINT=your-model-endpoint .venv/bin/python plain/run.py
```

Generation requests use an 8,000-token output limit; retries are capped at 10,000
tokens to stay within the default endpoint's limit.
