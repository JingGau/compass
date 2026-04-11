from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from tools.env_config import load_dotenv


@dataclass
class ContextPackage:
    step: int
    scene: str
    estimated_tokens: int
    content: dict[str, Any]
    excluded: list[str]


@dataclass
class AdapterContext:
    adapter_name: str
    readme: str
    config_summary: str
    estimated_tokens: int


def _is_cjk(ch: str) -> bool:
    cp = ord(ch)
    return (0x4E00 <= cp <= 0x9FFF or 0x3400 <= cp <= 0x4DBF
            or 0x20000 <= cp <= 0x2A6DF or 0xF900 <= cp <= 0xFAFF)


def estimate_tokens(text: str) -> int:
    """Estimate token count with CJK-aware weighting.

    CJK characters: ~2 tokens each; non-CJK: ~0.25 tokens each (1 per 4 chars).
    """
    cjk = sum(1 for ch in text if _is_cjk(ch))
    non_cjk = len(text) - cjk
    return max(1, int(cjk * 2 + non_cjk * 0.25))


class ContextInjector:
    def __init__(self, root: str | Path = ".") -> None:
        self.root = Path(root)
        load_dotenv(self.root)
        self.categories = self._load_yaml(self.root / "memory/categories.yaml")
        self.strategies = self._load_yaml(self.root / "memory/strategies.yaml")
        self._topology_cache: str | None = None

    def get_context(self, step: int, scene: str, state: dict[str, Any]) -> ContextPackage:
        main_prompt = self._prompt_for_step(step)
        snapshot = {
            "current_step": state.get("flow", {}).get("current_step"),
            "execution_mode": state.get("flow", {}).get("execution_mode"),
            "entities": state.get("entities", {}),
        }
        serialized = f"{main_prompt}\n{yaml.safe_dump(snapshot, allow_unicode=True, sort_keys=False)}"
        tokens = estimate_tokens(serialized)
        return ContextPackage(
            step=step,
            scene=scene,
            estimated_tokens=tokens,
            content={"main_prompt": main_prompt, "state_snapshot": snapshot},
            excluded=[],
        )

    def get_adapter_context(self, adapter_name: str) -> AdapterContext:
        """Load adapter-specific README and config for Step 6 on-demand."""
        readme_path = self.root / f"adapters/{adapter_name}/README.md"
        config_path = self.root / f"adapters/{adapter_name}/config.yaml"
        readme = ""
        if readme_path.exists():
            readme = readme_path.read_text(encoding="utf-8")
        config_summary = ""
        if config_path.exists():
            cfg = self._load_yaml(config_path)
            parts = [f"enabled: {cfg.get('enabled', True)}"]
            if "profiles" in cfg:
                for p in cfg["profiles"]:
                    parts.append(f"  - {p.get('name')}: {p.get('description', '')}")
            elif "projects" in cfg:
                parts.append(f"  envs: {list(cfg['projects'].keys())}")
            config_summary = "\n".join(parts)
        combined = f"{readme}\n{config_summary}"
        return AdapterContext(
            adapter_name=adapter_name,
            readme=readme,
            config_summary=config_summary,
            estimated_tokens=estimate_tokens(combined),
        )

    # -- per-step content assembly ----------------------------------------

    def _prompt_for_step(self, step: int) -> str:
        parts: list[str] = []
        if step == 1:
            parts.append(self._read_file("prompts/entity-extraction.md"))
        elif step == 2:
            parts.append(self._read_file("prompts/classify-scene.md"))
            parts.append(self._yaml_section("categories", self.categories))
        elif step == 3:
            parts.append(self._read_file("prompts/query-planning.md"))
            parts.append(self._topology_summary())
        elif step == 4:
            parts.append(self._read_file("prompts/query-planning.md"))
            parts.append(self._top_strategy_section())
            parts.append(self._topology_summary())
        elif step == 5:
            parts.append(self._read_file("guards/sql-safety.md"))
        elif step == 6:
            parts.append(self._read_file("prompts/query-planning.md"))
        elif step == 7:
            parts.append(self._read_file("prompts/result-analysis.md"))
        elif step == 8:
            parts.append(self._read_file("prompts/strategy-improvement.md"))
            parts.append(self._yaml_section("categories", self.categories))
        else:
            parts.append(self._read_file("SKILL.md"))
        return "\n\n".join(p for p in parts if p)

    # -- internal helpers --------------------------------------------------

    def _read_file(self, rel: str) -> str:
        p = self.root / rel
        if p.exists():
            return p.read_text(encoding="utf-8")
        return f"[文件不存在: {rel}]"

    def _yaml_section(self, key: str, data: dict) -> str:
        section = data.get(key)
        if section is None:
            return ""
        return yaml.safe_dump({key: section}, allow_unicode=True, sort_keys=False)

    def _topology_summary(self) -> str:
        if self._topology_cache is None:
            self._topology_cache = self._read_file("knowledge/system-topology.md")
        return self._topology_cache

    def _top_strategy_section(self) -> str:
        top_n = 3
        all_strategies = self.strategies.get("strategies", []) + self.strategies.get("presets", [])

        def _score(s: dict) -> float:
            sc = s.get("score", {})
            return sc.get("effectiveness", 0) * 0.5 + sc.get("usage_count", 0) * 0.1

        ranked = sorted(all_strategies, key=_score, reverse=True)[:top_n]
        if not ranked:
            return ""
        return yaml.safe_dump({"top_strategies": ranked}, allow_unicode=True, sort_keys=False)

    def _load_yaml(self, path: Path) -> dict[str, Any]:
        if not path.exists():
            return {}
        with path.open("r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
