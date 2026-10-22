# Wybrane Problemy Teorii Grafow - Graph Grammar Engine

This repository contains a modular Python implementation of a graph grammar engine (transformation system) created for the course "Wybrane problemy teorii grafow" (WPTG).

The program loads graph definitions and grammar productions from JSON files, checks consistency rules, matches subgraphs, and applies rewriting rules according to configurable strategies.

---

## Table of Contents

1. Project Overview
2. Project Structure
3. Data Formats (JSON)
   - Graph Specification
   - Grammar Specification
4. Core Concepts
   - Left-Hand Side (left) and Right-Hand Side (right)
   - Mapping (preserved nodes)
   - Embedding (reconnecting edges)
   - Handling Dangling Edges
   - Selection Strategy
5. System Architecture (TransformationSystem)
6. How to Install and Run
7. Example Derivation Walkthrough

---

## 1. Project Overview

A graph grammar works similarly to a formal string grammar, but instead of replacing substrings, it replaces subgraphs with other subgraphs:

1. Look for a subgraph in G matching the left side of a production.
2. Remove the parts of the matched subgraph that should not be preserved.
3. Insert the new vertices and edges defined by the right side.
4. Reconnect external edges from the removed vertices to the new vertices using embedding rules.
5. Record the step in history and optionally visualize the result.

---

## 2. Project Structure

```text
graph_grammar_project/
|
|-- data/
|   |-- initial_graph.json   # External starting graph (optional if defined in grammar)
|   `-- grammar_spec.json    # Grammar definition (labels, start graph, productions)
|
|-- src/
|   |-- __init__.py          # Module marker and public exports
|   |-- graph.py             # Graph, Vertex, Edge data structures
|   |-- production.py        # Production, Grammar, RuleEmbedding classes + validations
|   |-- engine.py            # TransformationSystem class (matching, apply, history)
|   |-- parser.py            # JSON loaders for graphs and grammars
|   `-- visualiser.py        # NetworkX and Matplotlib graph visualization
|
|-- output/                  # Generated step-by-step PNG visualization images
|-- main.py                  # Entry point
`-- README.md
```

---

## 3. Data Formats (JSON)

### Graph Specification (`data/initial_graph.json`)

A graph consists of vertices (with a unique `index` and a string `label`) and edges (connecting `u` and `v`, optionally with a `label` or `weight`):

```json
{
  "graph": {
    "directed": false,
    "name": "Przykladowy graf G",
    "vertices": [
      { "index": 0, "label": "A" },
      { "index": 1, "label": "B" },
      { "index": 2, "label": "C" },
      { "index": 3, "label": "D" }
    ],
    "edges": [
      { "u": 0, "v": 1 },
      { "u": 0, "v": 2 },
      { "u": 1, "v": 2 },
      { "u": 2, "v": 3, "weight": 4.5, "label": "most" }
    ]
  }
}
```

### Grammar Specification (`data/grammar_spec.json`)

A grammar defines global properties, alphabet labels, an optional starting graph, and an ordered list of productions:

```json
{
  "grammar": {
    "name": "Gramatyka sciezki",
    "directed": false,
    "danglingEdges": "forbid",

    "labels": {
      "nonterminals": ["S", "A"],
      "terminals": ["a", "b"]
    },

    "startGraph": {
      "vertices": [
        { "index": 0, "label": "S" }
      ],
      "edges": []
    },

    "productions": [
      {
        "name": "P1",
        "description": "S -> A - S",
        "left": {
          "vertices": [ { "index": 0, "label": "S" } ],
          "edges": []
        },
        "right": {
          "vertices": [
            { "index": 0, "label": "A" },
            { "index": 1, "label": "S" }
          ],
          "edges": [ { "u": 0, "v": 1 } ]
        },
        "mapping": [],
        "embedding": [
          { "leftVertex": 0, "neighborLabel": "*", "connectTo": [0] }
        ]
      }
    ]
  }
}
```

---

## 4. Core Concepts

### Left and Right Sides

- `left`: Pattern sought in the host graph.
- `right`: Replacement structure inserted where the pattern was found.

Vertex indices inside `left` and `right` are local to that production and are mapped independently.

### Mapping

An array of pairs `{ "left": i, "right": j }`.
- If a vertex from `left` is in `mapping`, it survives the transformation (its label may update if `right` specifies a new one). Its existing connections to the rest of the graph are retained.
- If a vertex from `left` is NOT in `mapping`, it is removed.
- If a vertex from `right` is NOT in `mapping`, it is newly created.

### Embedding

When a vertex is removed, any edge connecting it to external neighbors would be left hanging. The `embedding` section defines how to rewire them:

```json
"embedding": [
  {
    "leftVertex": 1,
    "neighborLabel": "C",
    "connectTo": [2]
  }
]
```
- `leftVertex`: Which removed vertex from `left` this rule targets.
- `neighborLabel`: Filter for external neighbors. Use `*` to match any label, or specify a exact label (e.g., `"C"`).
- `connectTo`: List of vertex indices in `right` where those incident edges should be reattached.

### Handling Dangling Edges

What happens if an external neighbor is not matched by any embedding rule?
- `danglingEdges: 1` (`forbid`): The production is cancelled and will not execute on this match.
- `danglingEdges: 2` (`delete`): The unhandled dangling edges are simply deleted along with the removed vertex.

### Node Selection Strategy

When multiple nodes or subgraphs match the production:
- `selection_strategy: 1` (`all_nodes`): The production is applied in parallel to all disjoint valid matches found in the graph.
- `selection_strategy: 2` (`min_id`): The production is applied only to the match containing the lowest vertex index.

---

## 5. System Architecture: `TransformationSystem`

The main execution engine is `TransformationSystem`, located in `src/engine.py`. It holds:

1. `G` (`Graph`): The current state of the working graph.
2. `T` (`Grammar`): The loaded grammar containing verified productions and label sets.
3. `History` (`List[Tuple[Production, Graph]]`): A list tracking each step: `(applied_production, resulting_graph_snapshot)`. Each snapshot is a detached deep copy so past states remain unmodified.
4. `apply(productions, selection_strategy, dangling_edges)`: The method that executes the sequence of production names or instances.

---

## 6. How to Install and Run

### Requirements

- Python 3.10+
- `networkx`
- `matplotlib`

Install dependencies:
```bash
pip install networkx matplotlib
```

### Running the Project

From the project root directory:
```bash
python main.py
```

What the script will do:
1. Load grammar rules from `data/grammar_spec.json` and initialize graph `G`.
2. Save initial visualization in `output/step_0_initial.png`.
3. Execute the defined sequence of productions through `ts.apply(...)`.
4. Store intermediate states in `ts.History` and save each step to `output/`.
5. Display the final terminal graph and check if all vertices are terminal labels.

---

## 7. Example Derivation Walkthrough

For the string of productions `[P1, P1, P3, P2, P2]` with starting node `S`:

1. `S` -> `A - S` via `P1` (new `S` is connected to `A`)
2. `A - S` -> `A - A - S` via `P1` (embedding keeps previous chain connected)
3. `A - A - S` -> `A - A - b` via `P3` (terminal `b` replaces nonterminal `S`)
4. `A - A - b` -> `a - A - b` via `P2` (first `A` becomes terminal `a`)
5. `a - A - b` -> `a - a - b` via `P2` (remaining `A` becomes `a`)

At the end, all labels `[a, a, b]` belong to `terminals`, which confirms that the final graph belongs to the language generated by the grammar.
