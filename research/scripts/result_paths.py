"""Locations for published research outputs in the repository."""

from pathlib import Path


def result_path(results: Path, filename: str) -> Path:
    """Route a repository result by file type, leaving custom run roots intact."""
    if results.name == "results" and results.parent.name == "research":
        if filename.endswith((".json", ".jsonl", ".json.gz", ".json.zlib")):
            return results.parent / "json" / results.name / filename
        if filename.endswith(".md"):
            return results.parent / "papers" / results.name / filename
    return results / filename
