import copy
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple


@dataclass
class Vertex:
    index: int
    label: str
    attributes: dict = field(default_factory=dict)


@dataclass
class Edge:
    u: int
    v: int
    label: Optional[str] = None
    weight: Optional[float] = None


class Graph:
    def __init__(self, name: str = "", directed: bool = False):
        self.name = name
        self.directed = directed
        self.vertices: Dict[int, Vertex] = {}
        self.adj: Dict[int, Dict[int, Edge]] = {}

    def copy(self) -> "Graph":
        """Tworzy niezależną (głęboką) kopię grafu na potrzeby obiektu History."""
        return copy.deepcopy(self)

    def add_vertex(self, index: int, label: str, attributes: Optional[dict] = None) -> Vertex:
        if index in self.vertices:
            raise ValueError(f"Duplikat indeksu wierzchołka: {index} w grafie '{self.name}'.")
        vertex = Vertex(index=index, label=label, attributes=attributes or {})
        self.vertices[index] = vertex
        self.adj[index] = {}
        return vertex

    def add_edge(self, u: int, v: int, label: Optional[str] = None, weight: Optional[float] = None):
        if u not in self.vertices or v not in self.vertices:
            raise ValueError(f"Krawędź ({u}, {v}) wskazuje na nieistniejący wierzchołek w grafie '{self.name}'.")
        edge = Edge(u=u, v=v, label=label, weight=weight)
        self.adj[u][v] = edge
        if not self.directed:
            self.adj[v][u] = edge

    def remove_edge(self, u: int, v: int):
        if u in self.adj and v in self.adj[u]:
            del self.adj[u][v]
        if not self.directed and v in self.adj and u in self.adj[v]:
            del self.adj[v][u]

    def remove_vertex(self, index: int):
        if index not in self.vertices:
            return
        for n in list(self.adj[index].keys()):
            self.remove_edge(index, n)
        del self.adj[index]
        del self.vertices[index]

    def get_neighbors(self, index: int) -> List[Tuple[Vertex, Edge]]:
        return [(self.vertices[n_idx], edge) for n_idx, edge in self.adj.get(index, {}).items()]

    def get_next_available_index(self) -> int:
        return max(self.vertices.keys(), default=-1) + 1

    def is_terminal(self, terminals: Set[str]) -> bool:
        return all(v.label in terminals for v in self.vertices.values())

    @classmethod
    def from_dict(cls, data: dict, default_directed: bool = False) -> "Graph":
        directed = data.get("directed", default_directed)
        g = cls(name=data.get("name", ""), directed=directed)
        for v in data.get("vertices", []):
            g.add_vertex(v["index"], v["label"], v.get("attributes"))
        for e in data.get("edges", []):
            g.add_edge(e["u"], e["v"], e.get("label"), e.get("weight"))
        return g

    def __repr__(self) -> str:
        nodes_str = ", ".join(f"{v.index}:{v.label}" for _, v in sorted(self.vertices.items()))
        edge_count = sum(len(x) for x in self.adj.values())
        if not self.directed:
            edge_count //= 2
        return f"Graph('{self.name}', |V|={len(self.vertices)}, |E|={edge_count}, Nodes=[{nodes_str}])"