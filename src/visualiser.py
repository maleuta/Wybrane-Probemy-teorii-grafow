import os
import matplotlib.pyplot as plt
import networkx as nx
from src.graph import Graph


def draw_graph(graph: Graph, title: str = "Wizualizacja Grafu", save_path: str = None, show: bool = True):
    G = nx.DiGraph() if graph.directed else nx.Graph()

    for idx, v in graph.vertices.items():
        G.add_node(idx, label=v.label)

    for u, neighbors in graph.adj.items():
        for v, edge in neighbors.items():
            if graph.directed or u <= v:
                lbl = edge.label or (str(edge.weight) if edge.weight is not None else "")
                G.add_edge(u, v, label=lbl)

    plt.figure(figsize=(8, 6))
    pos = nx.spring_layout(G, seed=42)

    if len(G.nodes) > 0:
        labels = [G.nodes[n]["label"] for n in G.nodes()]
        unique_labels = sorted(list(set(labels)))
        cmap = plt.colormaps["Set3"]
        label_to_color = {lbl: cmap(i / max(1, len(unique_labels))) for i, lbl in enumerate(unique_labels)}
        node_colors = [label_to_color[G.nodes[n]["label"]] for n in G.nodes()]

        nx.draw_networkx_nodes(G, pos, node_color=node_colors, node_size=1100, edgecolors="black", linewidths=1.5)
        node_labels = {n: f"{n}:{G.nodes[n]['label']}" for n in G.nodes()}
        nx.draw_networkx_labels(G, pos, labels=node_labels, font_size=10, font_weight="bold")

        nx.draw_networkx_edges(G, pos, width=1.8, alpha=0.8, edge_color="dimgray")
        edge_labels = {k: v for k, v in nx.get_edge_attributes(G, "label").items() if v}
        if edge_labels:
            nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, font_size=9)

    plt.title(title, fontsize=13, fontweight="bold")
    plt.axis("off")
    plt.tight_layout()

    if save_path:
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        plt.savefig(save_path, dpi=150)
        print(f"    [Zapisano wizualizację]: {save_path}")

    if show:
        plt.show()

    plt.close()