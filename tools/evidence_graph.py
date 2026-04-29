from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Any

from tools.action_cards import ActionResult


@dataclass(frozen=True)
class EvidenceNode:
    type: str
    value: str

    @property
    def id(self) -> str:
        return f"{self.type}:{self.value}"


@dataclass(frozen=True)
class EvidenceEdge:
    from_id: str
    to_id: str
    relation: str


class EvidenceGraph:
    def __init__(self) -> None:
        self._nodes: dict[str, EvidenceNode] = {}
        self._edges: set[EvidenceEdge] = set()

    def add_node(self, node_type: str, value: str) -> EvidenceNode:
        node = EvidenceNode(node_type, value)
        self._nodes.setdefault(node.id, node)
        return node

    def link(
        self,
        from_type: str,
        from_value: str,
        to_type: str,
        to_value: str,
        relation: str,
    ) -> None:
        from_node = self.add_node(from_type, from_value)
        to_node = self.add_node(to_type, to_value)
        self._edges.add(EvidenceEdge(from_node.id, to_node.id, relation))

    def add_result_leads(self, action_id: str, result: ActionResult) -> None:
        source = self.add_node("action", action_id)
        lead_types = {
            "interfaces": "api",
            "methods": "method",
            "tables": "table",
            "trace_ids": "trace",
            "keys": "key",
            "timestamps": "timestamp",
        }
        for lead_key, node_type in lead_types.items():
            for value in result.leads.get(lead_key, []):
                lead = self.add_node(node_type, value)
                self._edges.add(EvidenceEdge(source.id, lead.id, "extracts"))

    def to_dict(self) -> dict[str, list[dict[str, str]]]:
        nodes = [
            {"id": node.id, "type": node.type, "value": node.value}
            for node in sorted(self._nodes.values(), key=lambda item: item.id)
        ]
        edges = [
            {"from": edge.from_id, "to": edge.to_id, "relation": edge.relation}
            for edge in sorted(self._edges, key=lambda item: (item.from_id, item.to_id, item.relation))
        ]
        return {"nodes": nodes, "edges": edges}


def max_simple_path_length_edges(graph_dict: dict[str, Any]) -> int:
    """计算证据图中有向简单路径的最大边数（链路深度）。

    典型场景：action → api → method → table 等为一条链，
    depth=3 条边≈跨越 4 个节点。"""
    nodes = {str(n["id"]) for n in graph_dict.get("nodes", []) if n.get("id")}
    if not nodes:
        return 0
    adj: dict[str, list[str]] = defaultdict(list)
    for e in graph_dict.get("edges", []) or []:
        f_id, to_id = e.get("from"), e.get("to")
        if f_id in nodes and to_id in nodes:
            adj[str(f_id)].append(str(to_id))

    best = 0

    def dfs(u: str, path: frozenset[str]) -> int:
        max_len_local = 0
        for v in adj.get(u, []):
            if v not in path:
                max_len_local = max(max_len_local, 1 + dfs(v, path | {v}))
        return max_len_local

    for start in nodes:
        best = max(best, dfs(start, frozenset({start})))
    return best


def summarize_graph_nodes_for_bisect(graph_dict: dict[str, Any]) -> list[tuple[str, str]]:
    """返回 (类型, id) 列表供二分提示罗列中间节点候选（不去重拓扑序，仅取样）。"""
    out: list[tuple[str, str]] = []
    for n in sorted(graph_dict.get("nodes", []) or [], key=lambda x: str(x.get("id", ""))):
        nid = str(n.get("id", ""))
        parts = nid.split(":", 1)
        if len(parts) >= 2:
            out.append((parts[0], parts[1]))
    return out[:12]

