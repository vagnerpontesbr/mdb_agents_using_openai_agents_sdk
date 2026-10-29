"""Offline repository-foundation checks; no third-party dependencies or API calls."""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from urllib.parse import unquote, urlsplit


REQUIRED = (
    "AGENTS.md",
    "README.md",
    "initial_plan.md",
    "CONTRIBUTING.md",
    "SECURITY.md",
    ".gitignore",
    ".editorconfig",
    ".github/workflows/repository-checks.yml",
    ".github/pull_request_template.md",
    "docs/adr/README.md",
    "docs/tasks/README.md",
)
SKIP = {".git", ".venv", "node_modules", "artifacts", "dist", "build",
        ".pytest_cache", ".mypy_cache", ".ruff_cache"}
LINK = re.compile(r"!?\[[^\]\n]*\]\(([^\s)]+)(?:\s+\"[^\"]*\")?\)")


def prose(text: str) -> str:
    """Exclude fenced code examples from link checks."""
    return re.sub(r"(?ms)^\s*(`{3,}|~{3,})[^\n]*\n.*?^\s*\1\s*$", "", text)


def check(root: Path) -> tuple[list[str], int, int]:
    root = root.resolve()
    errors: list[str] = []
    for name in REQUIRED:
        if not (root / name).is_file():
            errors.append(f"Missing foundation file: {name}")
    markdown = sorted(
        p for p in root.rglob("*.md")
        if not any(part in SKIP for part in p.relative_to(root).parts)
    )
    for path in markdown:
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeError as exc:
            errors.append(f"{path.relative_to(root)}: invalid UTF-8 ({exc})")
            continue
        for match in LINK.finditer(prose(text)):
            target = match.group(1).strip("<>")
            parsed = urlsplit(target)
            if parsed.scheme or parsed.netloc or not parsed.path:
                continue
            destination = (path.parent / unquote(parsed.path)).resolve()
            if not destination.is_relative_to(root):
                errors.append(f"{path.relative_to(root)}: nonportable local link {target}")
            elif not destination.is_file():
                errors.append(f"{path.relative_to(root)}: missing local link {target}")
    adrs = sorted((root / "docs/adr").glob("[0-9][0-9][0-9][0-9]-*.md"))
    ids: set[str] = set()
    index_path = root / "docs/adr/README.md"
    index = index_path.read_text(encoding="utf-8") if index_path.is_file() else ""
    for path in adrs:
        number = path.name[:4]
        if number in ids:
            errors.append(f"Duplicate ADR ID: {number}")
        ids.add(number)
        text = path.read_text(encoding="utf-8")
        if not text.startswith(f"# ADR-{number}:"):
            errors.append(f"{path.name}: title/ID mismatch")
        for section in (
            "- Status:", "- Owner:", "## Context", "## Decision",
            "## Alternatives considered", "## Consequences and tradeoffs",
            "## Validation", "## Revisit trigger",
        ):
            if section not in text:
                errors.append(f"{path.name}: missing {section}")
        if f"]({path.name})" not in index:
            errors.append(f"{path.name}: missing ADR index entry")
    return errors, len(markdown), len(adrs)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    errors, documents, adrs = check(args.root.resolve())
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print(f"PASS: {documents} Markdown files, {adrs} ADRs, required foundation files.")
    print("Scope: local file links and ADR structure; not external URLs, anchors, secrets, or application compatibility.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
