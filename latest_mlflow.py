#!/usr/bin/env python3
"""Print the newest stable MLflow version listed by a PyPI Simple index."""

from __future__ import annotations

import re
import sys


STABLE_ARTIFACT = re.compile(
    r"mlflow-(\d+(?:\.\d+)+)(?:-py\d[^\"'<> ]*\.whl|\.tar\.gz)",
    re.IGNORECASE,
)


def latest_stable_mlflow(index_html: str) -> str:
    versions = {
        tuple(int(part) for part in match.group(1).split(".")): match.group(1)
        for match in STABLE_ARTIFACT.finditer(index_html)
    }
    if not versions:
        raise ValueError("package index listed no stable MLflow releases")
    return versions[max(versions)]


def main() -> int:
    try:
        print(latest_stable_mlflow(sys.stdin.read()))
    except ValueError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
