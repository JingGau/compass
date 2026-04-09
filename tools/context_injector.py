from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from tools.env_config import int_env, load_dotenv


@dataclass
class ContextPackage:
    step: int
    scene: str
    estimated_tokens: int
    content: dict[str, Any]
    excluded: list[str]


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


class ContextInjector:
    def __init__(self, root: str | Path = ".") -> None:
        self.root = Path(root)
        load_dotenv(self.root)
        self.context_limits = self._load_yaml(self.root / "guards/context-limits.yaml")

    def get_context(self, step: int, scene: str, state: dict[str, Any]) -> ContextPackage:
        main_prompt = self._prompt_for_step(step)
        snapshot = {
            "current_step": state.get("flow", {}).get("current_step"),
            "execution_mode": state.get("flow", {}).get("execution_mode"),
            "entities": state.get("entities", {}),
        }
        serialized = f"{main_prompt}\n{snapshot}"
        tokens = estimate_tokens(serialized)
        max_tokens = int_env(
            "HARN_PER_INJECTION_MAX_TOKENS",
            int(self.context_limits["per_injection"]["max_tokens"]),
        )
        if tokens > max_tokens:
            serialized = serialized[: max_tokens * 4]
            tokens = estimate_tokens(serialized)
        return ContextPackage(
            step=step,
            scene=scene,
            estimated_tokens=tokens,
            content={"main_prompt": main_prompt, "state_snapshot": snapshot},
            excluded=["非当前步骤文档", "全量原始查询数据"],
        )

    def _prompt_for_step(self, step: int) -> str:
        mapping = {
            1: "prompts/entity-extraction.md",
            2: "prompts/classify-scene.md",
            3: "prompts/query-planning.md",
            4: "prompts/query-planning.md",
            5: "guards/sql-safety.md",
            6: "adapters/",
            7: "prompts/result-analysis.md",
            8: "prompts/strategy-improvement.md",
        }
        target = mapping.get(step, "SKILL.md")
        return f"step={step}, primary={target}"

    def _load_yaml(self, path: Path) -> dict[str, Any]:
        with path.open("r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
