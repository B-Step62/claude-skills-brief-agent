"""Command-line entry point for the Claude Code brief generator.

    generate_brief(topic=None, date=None)

runs the pipeline end-to-end, writes the brief to
output/{date}-{topic-slug}.md, and returns the final state.

CLI:
    python run.py
    python run.py --topic "Claude Code MCP servers"
    python run.py --date 2026-07-22
"""
import argparse
import datetime
import logging
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from brief_agent import prompts  # noqa: E402
from brief_agent.graph import build_graph  # noqa: E402
from render import render_and_open  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger("brief_agent.run")


def generate_brief(topic: str | None = None, date: str | None = None) -> dict:
    """Run the brief pipeline. Returns the final graph state (includes `brief`
    and `output_path`)."""
    initial = {
        "topic": topic or prompts.DEFAULT_TOPIC,
        "date": date or datetime.date.today().strftime("%Y-%m-%d"),
    }

    app = build_graph()
    final = app.invoke(initial)
    return final


def _main() -> None:
    ap = argparse.ArgumentParser(description="Generate a Claude Code skills/plugins brief.")
    ap.add_argument("--topic", help="Topic to brief on (default: cool new Claude Code skills and plugins)")
    ap.add_argument("--date", help="Brief date YYYY-MM-DD (default today)")
    ap.add_argument("--no-open", action="store_true", help="Don't render/open the brief in the browser")
    a = ap.parse_args()

    final = generate_brief(topic=a.topic, date=a.date)
    topic = final.get("topic") or (a.topic or "")
    html_path = render_and_open(
        final.get("brief", ""), final.get("output_path"), topic, open_browser=not a.no_open,
    )
    print("\n" + "=" * 70)
    print("BRIEF (markdown):", final.get("output_path"))
    if html_path:
        print("BRIEF (opened in browser):", html_path)
    print("Results gathered:", final.get("result_count"))
    print("Brief chars:", len(final.get("brief") or ""))
    print("=" * 70)


if __name__ == "__main__":
    _main()
