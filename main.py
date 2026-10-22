import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from src.parser import load_graph_from_json, load_grammar_from_json
from src.engine import TransformationSystem
from src.visualiser import draw_graph


def main():
    grammar_path = os.path.join(BASE_DIR, "data", "grammar_spec.json")
    external_graph_path = os.path.join(BASE_DIR, "data", "initial_graph.json")

    print(f"--> Ładowanie gramatyki T: {grammar_path}")
    T, policy = load_grammar_from_json(grammar_path)

    if T.start_graph is not None:
        G = T.start_graph.copy()
        print("--> Użyto grafu startowego zdefiniowanego w gramatyce T.")
    else:
        print(f"--> Ładowanie grafu G z pliku: {external_graph_path}")
        G = load_graph_from_json(external_graph_path)

    print("\n[Stan Początkowy G]")
    print(G)
    draw_graph(G, title="Graf początkowy G0", save_path="output/step_0_initial.png", show=True)

    ts = TransformationSystem(G=G, T=T)

    sequence = policy.get("sequence", ["P1", "P2", "P3", "P4", "P5", "P6", "P7"])

    # 3. Wywołanie metody apply:
    #    selection_strategy: 1 = wszystkie pasujące węzły, 2 = węzeł o najniższym indeksie
    #    dangling_edges:     1 = anuluj produkcję,         2 = usuń wiszącą krawędź
    print(f"\n[Wykonywanie ts.apply({sequence}, selection_strategy=2, dangling_edges=1)]")
    ts.apply(
        productions=sequence,
        selection_strategy=2,
        dangling_edges=1
    )

    # 4. Przegląd zawartości listy ts.History: elementy postaci (zastosowana produkcja, graf wynikowy)
    print(f"\n[Historia transformacji (liczba zapisanych kroków: {len(ts.History)})]")
    for step_idx, (applied_prod, resulting_graph) in enumerate(ts.History, start=1):
        print(f"  Krok {step_idx}: po produkcji '{applied_prod.name}' -> {resulting_graph}")
        draw_graph(
            resulting_graph,
            title=f"Krok {step_idx}: po {applied_prod.name}",
            save_path=f"output/step_{step_idx}_{applied_prod.name}.png",
            show=False
        )

    print("\n[Stan Końcowy obiektu ts.G]")
    print(ts.G)
    if T.terminals:
        print("Czy graf wynikowy należy do języka gramatyki (tylko terminale)? ->", ts.G.is_terminal(T.terminals))

    draw_graph(ts.G, title="Graf Końcowy", save_path="output/step_final.png", show=True)


if __name__ == "__main__":
    main()