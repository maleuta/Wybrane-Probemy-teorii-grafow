import json
from typing import Optional, Tuple
from src.graph import Graph
from src.production import Grammar, Production


def load_graph_from_json(filepath: str) -> Graph:
    """Wczytuje graf z osobnego pliku JSON (np. data/initial_graph.json)."""
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
    graph_data = data.get("graph", data)
    return Graph.from_dict(graph_data)


def load_grammar_from_json(filepath: str) -> Tuple[Grammar, dict]:
    """
    Wczytuje gramatykę w formacie prowadzącego {"grammar": {...}}
    oraz opcjonalną sekcję executionPolicy.
    """
    with open(filepath, "r", encoding="utf-8") as f:
        raw_data = json.load(f)

    g_data = raw_data.get("grammar", raw_data)
    name = g_data.get("name", "Gramatyka")
    directed = g_data.get("directed", False)
    dangling_edges = g_data.get("danglingEdges", "forbid")

    labels_data = g_data.get("labels", {})
    nonterminals = set(labels_data.get("nonterminals", []))
    terminals = set(labels_data.get("terminals", []))

    start_graph: Optional[Graph] = None
    if "startGraph" in g_data:
        start_graph = Graph.from_dict(g_data["startGraph"], default_directed=directed)
        if not start_graph.name:
            start_graph.name = "StartGraph"

    productions = [
        Production.from_dict(p, default_directed=directed, default_dangling=dangling_edges)
        for p in g_data.get("productions", [])
    ]

    grammar = Grammar(
        name=name,
        directed=directed,
        dangling_edges=dangling_edges,
        nonterminals=nonterminals,
        terminals=terminals,
        start_graph=start_graph,
        productions=productions
    )

    policy = raw_data.get("executionPolicy", g_data.get("executionPolicy", {}))
    return grammar, policy