"""KB Learn 模块的单元测试。"""

from __future__ import annotations

from pathlib import Path

import pytest

from compass_core.knowledge import (
    KnowledgeError,
    list_knowledge,
    record_knowledge,
    search_knowledge,
    suggest_knowledge,
)


def test_record_knowledge_assigns_sequential_ids(tmp_path: Path) -> None:
    kb = tmp_path / "kb.yaml"
    a = record_knowledge(statement="A", path=kb)
    b = record_knowledge(statement="B", path=kb)
    c = record_knowledge(statement="C", path=kb)
    assert a["id"] == "K001"
    assert b["id"] == "K002"
    assert c["id"] == "K003"


def test_record_knowledge_dedupes_by_statement_and_merges_tags(tmp_path: Path) -> None:
    kb = tmp_path / "kb.yaml"
    record_knowledge(statement="同一陈述", tags=["a"], path=kb)
    second = record_knowledge(statement="同一陈述", tags=["b"], path=kb)
    items = list_knowledge(path=kb)
    assert len(items) == 1
    assert second["id"] == "K001"
    assert set(items[0]["tags"]) == {"a", "b"}


def test_record_rejects_empty_or_overlong(tmp_path: Path) -> None:
    kb = tmp_path / "kb.yaml"
    with pytest.raises(KnowledgeError):
        record_knowledge(statement="   ", path=kb)
    with pytest.raises(KnowledgeError):
        record_knowledge(statement="x" * 301, path=kb)


def test_suggest_orders_by_relevance(tmp_path: Path) -> None:
    kb = tmp_path / "kb.yaml"
    record_knowledge(
        statement="C 端订单号是 19 位数字",
        tags=["order", "id-rule"],
        path=kb,
    )
    record_knowledge(
        statement="OR 开头是 B 端 mock 数据",
        tags=["order", "mock"],
        path=kb,
    )
    record_knowledge(
        statement="充电订单与支付订单是不同表",
        tags=["order", "table"],
        path=kb,
    )
    matches = suggest_knowledge("用户订单 19 位数字", top_n=3, path=kb)
    assert matches
    assert matches[0].id == "K001"


def test_suggest_filters_by_tag(tmp_path: Path) -> None:
    kb = tmp_path / "kb.yaml"
    record_knowledge(statement="A", tags=["x"], path=kb)
    record_knowledge(statement="B", tags=["y"], path=kb)
    matches = suggest_knowledge("", tags=["x"], top_n=10, path=kb)
    assert {m.id for m in matches} == {"K001"}


def test_search_matches_id_tags_and_statement(tmp_path: Path) -> None:
    kb = tmp_path / "kb.yaml"
    record_knowledge(statement="陈述里有 foo 关键词", tags=["alpha"], path=kb)
    record_knowledge(statement="另一条 bar", tags=["beta"], path=kb)
    assert {item["id"] for item in search_knowledge("foo", path=kb)} == {"K001"}
    assert {item["id"] for item in search_knowledge("alpha", path=kb)} == {"K001"}
    assert {item["id"] for item in search_knowledge("k002", path=kb)} == {"K002"}
