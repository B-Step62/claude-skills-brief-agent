"""Hacker News and GitHub research helpers."""
from __future__ import annotations

import base64
import logging
import os

import requests
from bs4 import BeautifulSoup
from langchain_core.tools import tool

logger = logging.getLogger(__name__)

_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
_HEADERS = {"User-Agent": _UA, "Accept-Language": "en-US,en;q=0.9"}


def _github_headers() -> dict:
    """Build GitHub API headers, with optional token authentication."""
    headers = {**_HEADERS, "Accept": "application/vnd.github+json"}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


@tool
def hn_search(query: str, max_results: int = 6) -> list:
    """Search Hacker News stories (most recent first) via the Algolia API.

    Returns a list of {title, url, points, comments, date, source} dicts, or []
    on any failure."""
    try:
        resp = requests.get(
            "https://hn.algolia.com/api/v1/search_by_date",
            params={"query": query, "tags": "story", "hitsPerPage": max_results},
            headers=_HEADERS,
            timeout=20,
        )
        resp.raise_for_status()
        hits = resp.json().get("hits", [])
    except Exception as e:
        logger.warning("hn_search failed for %r: %s", query, e)
        return []

    out = []
    for h in hits:
        try:
            object_id = h.get("objectID")
            out.append({
                "title": h.get("title") or h.get("story_title") or "(untitled)",
                "url": h.get("url") or (f"https://news.ycombinator.com/item?id={object_id}" if object_id else ""),
                "points": h.get("points") or 0,
                "comments": h.get("num_comments") or 0,
                "date": (h.get("created_at") or "")[:10] or "unknown-date",
                "source": "Hacker News",
            })
        except Exception:
            continue
    return out


@tool
def github_search(query: str, max_results: int = 6, sort: str = "stars") -> list:
    """Search GitHub repositories via the public search API.

    sort: "stars" (most popular) or "updated" (most recently active). Returns a
    list of {title, url, description, stars, updated, source} dicts, or [] on any
    failure."""
    try:
        resp = requests.get(
            "https://api.github.com/search/repositories",
            params={"q": query, "sort": sort, "order": "desc", "per_page": max_results},
            headers=_github_headers(),
            timeout=20,
        )
        resp.raise_for_status()
        items = resp.json().get("items", [])
    except Exception as e:
        logger.warning("github_search failed for %r: %s", query, e)
        return []

    out = []
    for it in items:
        try:
            out.append({
                "title": it.get("full_name") or "(unnamed)",
                "url": it.get("html_url") or "",
                "description": (it.get("description") or "").strip(),
                "stars": it.get("stargazers_count") or 0,
                "updated": (it.get("pushed_at") or "")[:10] or "unknown-date",
                "source": "GitHub",
            })
        except Exception:
            continue
    return out


@tool
def github_readme(full_name: str, max_chars: int = 4000) -> str:
    """Fetch a repo's README text via the GitHub API (`repos/{full_name}/readme`).

    `full_name` is "owner/repo". Returns the decoded README (light markdown
    stripped to plain-ish text), truncated to max_chars, or "" on any failure."""
    if not full_name or "/" not in full_name:
        return ""
    try:
        resp = requests.get(
            f"https://api.github.com/repos/{full_name}/readme",
            headers=_github_headers(),
            timeout=20,
        )
        resp.raise_for_status()
        payload = resp.json()
    except Exception as e:
        logger.warning("github_readme failed for %s: %s", full_name, e)
        return ""

    try:
        content = payload.get("content") or ""
        if payload.get("encoding") == "base64" and content:
            text = base64.b64decode(content).decode("utf-8", errors="replace")
        else:
            text = content
        cleaned = []
        for line in text.splitlines():
            s = line.strip()
            if s.startswith("<!--") or s.startswith("![") or "img.shields.io" in s:
                continue
            cleaned.append(line)
        out = "\n".join(cleaned).strip()
        return out[:max_chars]
    except Exception:
        logger.exception("Failed to decode README for %s", full_name)
        return ""


@tool
def web_fetch(url: str, max_chars: int = 3500) -> str:
    """Fetch a URL and return its extracted text, truncated. Returns "" on any failure.

    Best-effort enrichment for a single top link. Not every page allows scraping,
    so callers must tolerate an empty string."""
    try:
        resp = requests.get(url, headers=_HEADERS, timeout=20)
        resp.raise_for_status()
    except Exception as e:
        logger.warning("web_fetch failed for %s: %s", url, e)
        return ""

    try:
        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()
        text = soup.get_text(separator=" ", strip=True)
        return text[:max_chars]
    except Exception:
        logger.exception("Failed to parse web_fetch content for %s", url)
        return ""
