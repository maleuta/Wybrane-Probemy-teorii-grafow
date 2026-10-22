from dataclasses import dataclass
from typing import Dict, List, Optional, Set
from src.graph import Graph


@dataclass
class RuleEmbedding:
    left_vertex: int
    neighbor_label: str
    connect_to: List[int]


@dataclass
class NegativeCondition:
    left_vertex: int
    forbidden_label: str


class Production:
    def __init__(
        self,
        name: str,
        left: Graph,
        right: Graph,
        mapping: Dict[int, int],
        embeddings: List[RuleEmbedding],
        description: str = "",
        negative_conditions: Optional[List[NegativeCondition]] = None,
        priority: int = 1,
        dangling_edges: str = "forbid",
        strict_embedding_validation: bool = False
    ):
        self.name = name
        self.description = description
        self.left = left
        self.right = right
        self.mapping = mapping
        self.embeddings = embeddings
        self.negative_conditions = negative_conditions or []
        self.priority = priority
        self.dangling_edges = dangling_edges
        self.validate(strict_embedding_validation)

    def validate(self, strict_embedding: bool = False):
        """Sprawdza zasady poprawności pojedynczej produkcji."""
        # Z2: mapping jest różnowartościowe (injekcja)
        if len(set(self.mapping.values())) != len(self.mapping):
            raise ValueError(f"Produkcja '{self.name}': mapping nie jest różnowartościowe po prawej stronie.")

        for l_idx, r_idx in self.mapping.items():
            if l_idx not in self.left.vertices:
                raise ValueError(f"Produkcja '{self.name}': mapping wskazuje nieistniejący wierzchołek left={l_idx}.")
            if r_idx not in self.right.vertices:
                raise ValueError(f"Produkcja '{self.name}': mapping wskazuje nieistniejący wierzchołek right={r_idx}.")

        # Z3: poprawność odwołań w embedding
        for emb in self.embeddings:
            if emb.left_vertex not in self.left.vertices:
                raise ValueError(f"Produkcja '{self.name}': leftVertex={emb.left_vertex} nie istnieje w left.")
            if strict_embedding and emb.left_vertex in self.mapping:
                raise ValueError(
                    f"Produkcja '{self.name}': leftVertex={emb.left_vertex} jest w mapping (nie jest usuwany)."
                )
            for target_r in emb.connect_to:
                if target_r not in self.right.vertices:
                    raise ValueError(
                        f"Produkcja '{self.name}': connectTo wskazuje nieistniejący wierzchołek right={target_r}."
                    )

        if self.dangling_edges not in ("forbid", "delete"):
            raise ValueError(f"Produkcja '{self.name}': nieznana opcja danglingEdges='{self.dangling_edges}'.")

    @classmethod
    def from_dict(cls, data: dict, default_directed: bool = False, default_dangling: str = "forbid") -> "Production":
        directed = data.get("directed", default_directed)
        dangling = data.get("danglingEdges", default_dangling)

        left = Graph.from_dict(data["left"], default_directed=directed)
        right = Graph.from_dict(data["right"], default_directed=directed)

        # walidacja unikalności w mapping po l stronie
        raw_mapping = data.get("mapping", [])
        left_keys = [m["left"] for m in raw_mapping]
        if len(left_keys) != len(set(left_keys)):
            raise ValueError(f"Produkcja '{data.get('name')}': powtórzony indeks 'left' w mapping.")

        mapping = {m["left"]: m["right"] for m in raw_mapping}

        embeddings = [
            RuleEmbedding(
                left_vertex=emb["leftVertex"],
                neighbor_label=emb["neighborLabel"],
                connect_to=emb["connectTo"]
            )
            for emb in data.get("embedding", [])
        ]

        neg_conditions = []
        for cond in data.get("negativeConditions", []):
            for item in cond.get("forbiddenNeighbors", []):
                neg_conditions.append(
                    NegativeCondition(
                        left_vertex=item["leftVertex"],
                        forbidden_label=item["neighborLabel"]
                    )
                )

        return cls(
            name=data.get("name", "P"),
            description=data.get("description", ""),
            left=left,
            right=right,
            mapping=mapping,
            embeddings=embeddings,
            negative_conditions=neg_conditions,
            priority=data.get("priority", 1),
            dangling_edges=dangling
        )


class Grammar:
    def __init__(
        self,
        name: str,
        directed: bool,
        dangling_edges: str,
        nonterminals: Set[str],
        terminals: Set[str],
        start_graph: Optional[Graph],
        productions: List[Production]
    ):
        self.name = name
        self.directed = directed
        self.dangling_edges = dangling_edges
        self.nonterminals = nonterminals
        self.terminals = terminals
        self.start_graph = start_graph
        self.productions = productions
        self.validate()

    def validate(self):
        """Sprawdza 5 zasad poprawności całej gramatyki."""
        if not self.nonterminals and not self.terminals:
            return 

        # 1 zbiory nonterminals i terminals są rozłączne
        overlap = self.nonterminals & self.terminals
        if overlap:
            raise ValueError(f"Gramatyka '{self.name}': zbiory terminalne i nieterminalne nie są rozłączne: {overlap}")

        all_allowed = self.nonterminals | self.terminals

        # 2 każda etykieta w startGraph należy do jednego ze zbiorów
        if self.start_graph:
            for v in self.start_graph.vertices.values():
                if v.label not in all_allowed:
                    raise ValueError(f"StartGraph zawiera nieznaną etykietę: '{v.label}'.")

        # 3 nazwy produkcji są unikalne
        prod_names = [p.name for p in self.productions]
        if len(prod_names) != len(set(prod_names)):
            raise ValueError(f"Gramatyka '{self.name}': nazwy produkcji nie są unikalne.")

        for p in self.productions:
            # 2cd. Etykiety w produkcjach należą do zbiorów
            for v in list(p.left.vertices.values()) + list(p.right.vertices.values()):
                if v.label not in all_allowed:
                    raise ValueError(f"Produkcja '{p.name}' używa nieznanej etykiety '{v.label}'.")

            # 3. Lewa strona zawiera co najmniej jeden nieterminal
            if not any(v.label in self.nonterminals for v in p.left.vertices.values()):
                raise ValueError(f"Produkcja '{p.name}': lewa strona musi zawierać co najmniej jeden nieterminal.")