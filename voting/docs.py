from __future__ import annotations

import re
from importlib import resources

DOCS: dict[str, dict] = {
    "overview": {
        "title": "Package Overview",
        "summary": "What this tool does, key concepts, and when to use it.",
        "file": "overview.md",
    },
    "getting-started": {
        "title": "Getting Started",
        "summary": "Step-by-step guide from init through first count.",
        "file": "getting-started.md",
    },
    "workflow": {
        "title": "Workflow & Phases",
        "summary": "The six phases and direct, synthetic, and hosted-human preference paths.",
        "file": "workflow.md",
    },
    "humanize": {
        "title": "Humanize Surveys",
        "summary": "Publish hosted voting surveys, share URLs, send email invitations, and retrieve responses.",
        "file": "humanize.md",
    },
    "ballot-types": {
        "title": "Ballot Types",
        "summary": "single_choice, ranked, approval, score, grade, and allocated ballot formats.",
        "file": "ballot-types.md",
    },
    "voting-methods": {
        "title": "Voting Methods",
        "summary": "All 32 supported method names and aliases grouped by category, with selection guidance.",
        "file": "voting-methods.md",
    },
    "data-model": {
        "title": "Data Model",
        "summary": "Directory layout of .voting/ and JSON schemas for each file type.",
        "file": "data-model.md",
    },
    "troubleshooting": {
        "title": "Troubleshooting",
        "summary": "Common errors, warning codes, and their recovery hints.",
        "file": "troubleshooting.md",
    },
    "recipes": {
        "title": "Recipes",
        "summary": "Worked organizational patterns — prioritization, hiring panels, preference surveys, AI pretesting, budget allocation.",
        "file": "recipes.md",
    },
}


def load_doc(topic: str) -> str:
    meta = DOCS[topic]
    pkg = resources.files("voting").joinpath("docs_content")
    return pkg.joinpath(meta["file"]).read_text(encoding="utf-8")


def search_docs(query: str) -> list[dict]:
    terms = re.findall(r"[A-Za-z0-9_-]+", query.lower())
    if not terms:
        return []
    results = []
    for topic, meta in DOCS.items():
        text = load_doc(topic)
        haystack = f"{topic} {meta['title']} {meta['summary']} {text}".lower()
        score = sum(haystack.count(t) for t in terms)
        if score == 0:
            continue
        snippet = ""
        for term in terms:
            idx = haystack.find(term)
            if idx >= 0:
                start = max(0, idx - 80)
                end = min(len(text), idx + 200)
                snippet = text[start:end].strip()
                break
        results.append({**meta, "topic": topic, "score": score, "snippet": snippet})
    return sorted(results, key=lambda r: r["score"], reverse=True)
