from __future__ import annotations

from dataclasses import dataclass

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

