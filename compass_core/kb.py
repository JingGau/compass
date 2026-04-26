from __future__ import annotations

import os
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass(frozen=True)
class KnowledgeMatch:
    path: str
    line: int
    snippet: str

    def to_dict(self) -> dict:
        return asdict(self)


def default_roots(project_root: Path) -> list[Path]:
    roots = [project_root / "knowledge", project_root / "projects", project_root / "docs"]
    obsidian = os.environ.get("COMPASS_OBSIDIAN_ROOT")
    if obsidian:
        roots.append(Path(obsidian).expanduser())
    return roots


def search_markdown(query: str, roots: list[Path], limit: int = 10) -> list[KnowledgeMatch]:
    needle = query.casefold()
    matches: list[KnowledgeMatch] = []
    for root in roots:
        root = root.expanduser()
        if not root.exists():
            continue
        for path in sorted(root.rglob("*.md")):
            if _is_hidden(path):
                continue
            try:
                lines = path.read_text(encoding="utf-8").splitlines()
            except UnicodeDecodeError:
                continue
            for index, line in enumerate(lines, start=1):
                if needle in line.casefold():
                    matches.append(KnowledgeMatch(path=str(path), line=index, snippet=_snippet(line)))
                    if len(matches) >= limit:
                        return matches
    return matches


def _is_hidden(path: Path) -> bool:
    return any(part.startswith(".") for part in path.parts)


def _snippet(line: str, width: int = 160) -> str:
    text = " ".join(line.strip().split())
    if len(text) <= width:
        return text
    return text[: width - 3] + "..."

