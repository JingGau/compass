"""通用知识库（KB Learn）。

设计目标：让 Agent / 用户在排查过程中沉淀"小颗粒、可复用、跨问题"的通用知识，
并在新会话开场时自动召回最相关的若干条作为上下文，缩短无效摸索路径。

存储格式：
    memory/knowledge.yaml
        knowledge:
          - id: K001
            tags: [order, id-rule]
            statement: "C 端订单号格式为 19 位数字..."
            evidence: ["E1"]            # 可选，最初学到时的证据 id
            created_at: "2026-..."
            updated_at: "2026-..."
            source_session: "sess_..."  # 可选
            hits: 0                      # 命中计数（召回后递增）

约束：
    - statement 限制 ≤ 300 字（避免变成大段文档），便于直接注入上下文。
    - 不存放任何敏感数据，statement 中如出现银行卡 / 身份证等需先脱敏。
    - 与 markdown KB（knowledge/ 目录）正交：markdown 适合"长文档/系统拓扑"，
      yaml KB 适合"一句话事实/规则"。
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import yaml

from .state import now_iso

MAX_STATEMENT_LEN = 300
DEFAULT_RECALL_TOP_N = 5


class KnowledgeError(Exception):
    """KB 录入/召回相关的领域异常。"""


@dataclass(frozen=True)
class KnowledgeMatch:
    """召回结果。"""

    id: str
    statement: str
    tags: list[str]
    score: float
    hits: int
    evidence: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "statement": self.statement,
            "tags": list(self.tags),
            "score": round(self.score, 4),
            "hits": self.hits,
            "evidence": list(self.evidence),
        }


def _kb_path(project_root: str | Path | None = None) -> Path:
    if project_root is None:
        project_root = Path(__file__).resolve().parent.parent
    return Path(project_root) / "memory" / "knowledge.yaml"


def load_kb(path: str | Path | None = None) -> dict[str, Any]:
    file_path = Path(path) if path else _kb_path()
    if not file_path.exists():
        return {"knowledge": []}
    raw = file_path.read_text(encoding="utf-8")
    if not raw.strip():
        return {"knowledge": []}
    try:
        data = yaml.safe_load(raw) or {}
    except yaml.YAMLError as exc:
        raise KnowledgeError(f"知识库文件格式错误：{file_path} ({exc})") from exc
    if not isinstance(data, dict):
        raise KnowledgeError(f"知识库根节点必须是 mapping：{file_path}")
    knowledge = data.get("knowledge") or []
    if not isinstance(knowledge, list):
        raise KnowledgeError(f"knowledge 字段必须是 list：{file_path}")
    return {"knowledge": knowledge}


def save_kb(data: dict[str, Any], path: str | Path | None = None) -> None:
    file_path = Path(path) if path else _kb_path()
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(
        yaml.safe_dump(
            {"knowledge": data.get("knowledge") or []},
            allow_unicode=True,
            sort_keys=False,
        ),
        encoding="utf-8",
    )


def _next_id(items: Iterable[dict[str, Any]]) -> str:
    max_n = 0
    for item in items:
        kid = str(item.get("id", "")).strip()
        match = re.match(r"K(\d+)", kid)
        if match:
            try:
                max_n = max(max_n, int(match.group(1)))
            except ValueError:
                continue
    return f"K{max_n + 1:03d}"


def _normalize_tags(tags: Iterable[str] | None) -> list[str]:
    if not tags:
        return []
    seen: list[str] = []
    for tag in tags:
        if tag is None:
            continue
        t = str(tag).strip().lower()
        if t and t not in seen:
            seen.append(t)
    return seen


def record_knowledge(
    *,
    statement: str,
    tags: Iterable[str] | None = None,
    evidence: Iterable[str] | None = None,
    source_session: str | None = None,
    path: str | Path | None = None,
) -> dict[str, Any]:
    """录入一条知识。"""

    text = (statement or "").strip()
    if not text:
        raise KnowledgeError("statement 不能为空。")
    if len(text) > MAX_STATEMENT_LEN:
        raise KnowledgeError(
            f"statement 长度 {len(text)} 超过上限 {MAX_STATEMENT_LEN}；"
            "请精简成一句话事实或规则，长文档请放 knowledge/ 目录。"
        )
    normalized_tags = _normalize_tags(tags)

    data = load_kb(path)
    items = list(data.get("knowledge") or [])
    for item in items:
        if str(item.get("statement", "")).strip() == text:
            existing_tags = _normalize_tags(item.get("tags"))
            merged = list(dict.fromkeys(existing_tags + normalized_tags))
            item["tags"] = merged
            item["updated_at"] = now_iso()
            save_kb({"knowledge": items}, path)
            return dict(item)

    new_id = _next_id(items)
    record = {
        "id": new_id,
        "tags": normalized_tags,
        "statement": text,
        "evidence": list(evidence or []),
        "source_session": source_session or "",
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "hits": 0,
    }
    items.append(record)
    save_kb({"knowledge": items}, path)
    return dict(record)


def list_knowledge(path: str | Path | None = None) -> list[dict[str, Any]]:
    return list(load_kb(path).get("knowledge") or [])


def _tokenize(text: str) -> list[str]:
    """轻量分词：保留中英文连续片段，长度 ≥ 2。"""

    text = (text or "").lower()
    tokens = re.findall(r"[a-z0-9_]+|[\u4e00-\u9fff]+", text)
    out: list[str] = []
    for tok in tokens:
        if re.match(r"[\u4e00-\u9fff]+", tok):
            for size in (3, 2):
                for i in range(len(tok) - size + 1):
                    out.append(tok[i : i + size])
        elif len(tok) >= 2:
            out.append(tok)
    return out


def _score(query_tokens: set[str], item: dict[str, Any], query_text: str) -> float:
    statement = str(item.get("statement", ""))
    item_tokens = set(_tokenize(statement))
    overlap = len(query_tokens & item_tokens)
    base = float(overlap)

    tags = _normalize_tags(item.get("tags"))
    q_lower = query_text.lower()
    tag_bonus = sum(2.0 for t in tags if t and t in q_lower)

    statement_lower = statement.lower()
    substr_bonus = 0.0
    for tok in query_tokens:
        if len(tok) >= 3 and tok in statement_lower:
            substr_bonus += 1.0

    hits = float(item.get("hits", 0) or 0)
    hits_bonus = min(hits, 10) * 0.1

    return base + tag_bonus + substr_bonus + hits_bonus


def suggest_knowledge(
    query: str,
    *,
    tags: Iterable[str] | None = None,
    top_n: int = DEFAULT_RECALL_TOP_N,
    path: str | Path | None = None,
    min_score: float = 1.0,
) -> list[KnowledgeMatch]:
    """按 query/tags 召回相关知识。"""

    items = list_knowledge(path)
    if not items:
        return []
    query_text = (query or "").strip()
    explicit_tags = _normalize_tags(tags)
    query_tokens = set(_tokenize(query_text)) | set(explicit_tags)

    scored: list[tuple[float, dict[str, Any]]] = []
    for item in items:
        item_tags = _normalize_tags(item.get("tags"))
        if explicit_tags and not (set(explicit_tags) & set(item_tags)):
            score = _score(query_tokens, item, query_text)
            if score < min_score:
                continue
        else:
            score = _score(query_tokens, item, query_text)
            if explicit_tags:
                score += 1.0
            if score < min_score and not explicit_tags:
                continue
        scored.append((score, item))

    scored.sort(key=lambda x: (-x[0], -int(x[1].get("hits", 0) or 0), x[1].get("id", "")))
    out: list[KnowledgeMatch] = []
    for score, item in scored[:top_n]:
        out.append(
            KnowledgeMatch(
                id=str(item.get("id", "")),
                statement=str(item.get("statement", "")),
                tags=_normalize_tags(item.get("tags")),
                score=score,
                hits=int(item.get("hits", 0) or 0),
                evidence=list(item.get("evidence") or []),
            )
        )
    return out


def increment_hits(ids: Iterable[str], path: str | Path | None = None) -> None:
    """召回成功后调用，递增 hits 计数。"""

    target = set(str(i) for i in ids if i)
    if not target:
        return
    data = load_kb(path)
    items = list(data.get("knowledge") or [])
    changed = False
    for item in items:
        if str(item.get("id", "")) in target:
            item["hits"] = int(item.get("hits", 0) or 0) + 1
            item["updated_at"] = now_iso()
            changed = True
    if changed:
        save_kb({"knowledge": items}, path)


def search_knowledge(
    query: str,
    *,
    path: str | Path | None = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """按 query 模糊匹配 statement / tags / id，返回最多 limit 条。"""

    q = (query or "").strip().lower()
    items = list_knowledge(path)
    if not q:
        return items[:limit]
    out: list[dict[str, Any]] = []
    for item in items:
        statement = str(item.get("statement", "")).lower()
        tags = " ".join(_normalize_tags(item.get("tags")))
        kid = str(item.get("id", "")).lower()
        if q in statement or q in tags or q in kid:
            out.append(dict(item))
            if len(out) >= limit:
                break
    return out
