import itertools
from typing import Dict, List, Optional, Set, Tuple, Union
from src.graph import Graph
from src.production import Grammar, Production


class TransformationSystem:
    """
    Klasa TransformationSystem:
    1. G: obiekt klasy Graph
    2. T: obiekt klasy Grammar
    3. History: lista elementów postaci (zastosowana produkcja, graf wynikowy)
    """

    SELECTION_ALL_NODES = 1   # 1 = każda produkcja stosowana do wszystkich pasujących węzłów
    SELECTION_MIN_INDEX = 2   # 2 = każda produkcja stosowana jedynie do pasującego węzła o najniższym indeksie

    DANGLING_FORBID = 1       # 1 = wykonanie produkcji jest anulowane przy braku transformacji osadzenia
    DANGLING_DELETE = 2       # 2 = usuwana jest każda wisząca krawędź bez transformacji osadzenia

    def __init__(self, G: Graph, T: Grammar):
        self.G: Graph = G
        self.T: Grammar = T
        self.History: List[Tuple[Production, Graph]] = []
        self._productions_map: Dict[str, Production] = {p.name: p for p in T.productions}

    # sprawdz wiszących krawędź
    def _has_unhandled_dangling_edges(self, prod: Production, match: Dict[int, int]) -> bool:
        """
        Sprawdza, czy dla danego dopasowania istnieje wisząca krawędź od usuwanego wierzchołka,
        dla której NIE zdefiniowano reguły osadzenia (embedding).
        """
        matched_g_nodes = set(match.values())
        deleted_left_nodes = [l_id for l_id in prod.left.vertices if l_id not in prod.mapping]

        for l_id in deleted_left_nodes:
            g_id = match[l_id]
            for neighbor, _ in self.G.get_neighbors(g_id):
                if neighbor.index not in matched_g_nodes:
                    covered = any(
                        rule.left_vertex == l_id and rule.neighbor_label in ("*", neighbor.label)
                        for rule in prod.embeddings
                    )
                    if not covered:
                        return True
        return False

    # wyszuk dopasowań w grafie G
    def _find_matches(self, prod: Production, dangling_policy: int) -> List[Dict[int, int]]:
        """
        Zwraca listę dopasowań {left_idx: graph_idx} posortowaną rosnąco po indeksach wierzchołków G.
        Uwzględnia obsługę wiszących krawędzi (dangling_policy == 1 anuluje dopasowanie z wiszącą krawędzią).
        """
        left_indices = sorted(prod.left.vertices.keys())
        graph_indices = sorted(self.G.vertices.keys())

        if len(left_indices) > len(graph_indices):
            return []

        valid_matches = []

        for combo in itertools.permutations(graph_indices, len(left_indices)):
            match = dict(zip(left_indices, combo))

            # 1. Sprawdzenie etykiet wierzchołków
            if not all(self.G.vertices[g_id].label == prod.left.vertices[l_id].label for l_id, g_id in match.items()):
                continue

            # 2. Sprawdzenie krawędzi wzorca
            edges_ok = True
            for u_l, neighbors in prod.left.adj.items():
                for v_l, e_l in neighbors.items():
                    u_g, v_g = match[u_l], match[v_l]
                    edge_in_g = self.G.adj.get(u_g, {}).get(v_g)
                    if edge_in_g is None or (e_l.label is not None and edge_in_g.label != e_l.label):
                        edges_ok = False
                        break
                if not edges_ok:
                    break
            if not edges_ok:
                continue

            # 3. Sprawdzenie warunków negatywnych (NAC)
            conflict = False
            for cond in prod.negative_conditions:
                g_node = match[cond.left_vertex]
                for neighbor, _ in self.G.get_neighbors(g_node):
                    if neighbor.index not in match.values() and neighbor.label == cond.forbidden_label:
                        conflict = True
                        break
                if conflict:
                    break
            if conflict:
                continue

            # 4. Obsługa wiszących krawędzi (opcja 1: anulowanie przy braku transformacji osadzenia)
            if dangling_policy == self.DANGLING_FORBID:
                if self._has_unhandled_dangling_edges(prod, match):
                    continue

            valid_matches.append(match)

        return valid_matches

    # zastosowanie prod do pojedynczego zastosowania
    def _apply_to_match(self, prod: Production, match: Dict[int, int]):
        matched_g_nodes = set(match.values())
        nodes_to_delete = [l_id for l_id in prod.left.vertices if l_id not in prod.mapping]

        # 1. Zapisz krawędzie zewnętrzne dla reguł embedding
        external_edges: List[Tuple[int, int, str, Optional[str]]] = []
        embedding_left_vertices = {rule.left_vertex for rule in prod.embeddings}

        for l_id in set(nodes_to_delete) | embedding_left_vertices:
            if l_id not in match:
                continue
            g_id = match[l_id]
            for neighbor, edge in self.G.get_neighbors(g_id):
                if neighbor.index not in matched_g_nodes:
                    external_edges.append((l_id, neighbor.index, neighbor.label, edge.label))

        # 2. Usuń krawędzie wewnętrzne lewej strony pomiędzy zachowanymi wierzchołkami
        for u_l, neighbors in prod.left.adj.items():
            for v_l in neighbors:
                if u_l in prod.mapping and v_l in prod.mapping:
                    self.G.remove_edge(match[u_l], match[v_l])

        # 3. Usuń wierzchołki niebędące w mapping
        # (Przy opcji dangling_edges == 2 nieobsłużone wiszące krawędzie zostają tu automatycznie usunięte)
        for l_id in nodes_to_delete:
            self.G.remove_vertex(match[l_id])

        # 4. Dodaj nowe lub zaktualizuj zachowane wierzchołki prawej strony
        right_to_graph: Dict[int, int] = {}
        for r_id, r_vertex in prod.right.vertices.items():
            left_id = next((l for l, r in prod.mapping.items() if r == r_id), None)
            if left_id is not None:
                g_id = match[left_id]
                self.G.vertices[g_id].label = r_vertex.label
                right_to_graph[r_id] = g_id
            else:
                new_id = self.G.get_next_available_index()
                self.G.add_vertex(new_id, r_vertex.label, r_vertex.attributes)
                right_to_graph[r_id] = new_id

        # 5. Dodaj krawędzie wewnętrzne prawej strony
        for u_r, neighbors in prod.right.adj.items():
            for v_r, edge in neighbors.items():
                u_g, v_g = right_to_graph[u_r], right_to_graph[v_r]
                if v_g not in self.G.adj.get(u_g, {}):
                    self.G.add_edge(u_g, v_g, edge.label, edge.weight)

        # 6. Przepnij krawędzie objęte regułami osadzenia (embedding)
        for l_id, neighbor_g_id, neighbor_label, edge_label in external_edges:
            if neighbor_g_id not in self.G.vertices:
                continue
            for rule in prod.embeddings:
                if rule.left_vertex == l_id and rule.neighbor_label in ("*", neighbor_label):
                    for target_r_id in rule.connect_to:
                        target_g_id = right_to_graph[target_r_id]
                        if target_g_id not in self.G.adj.get(neighbor_g_id, {}):
                            self.G.add_edge(neighbor_g_id, target_g_id, edge_label)

    # APPLY
    def apply(
        self,
        productions: List[Union[str, Production]],
        selection_strategy: int = 2,
        dangling_edges: Optional[int] = None
    ) -> List[Tuple[Production, Graph]]:
        """
        Stosuje listę produkcji z gramatyki T do obiektu G i dopisuje wyniki do History.

        Parametry:
        - productions: lista obiektów Production lub ich nazw (np. ["P1", "P2", ...])
        - selection_strategy:
            1 = każda produkcja stosowana do wszystkich pasujących węzłów
            2 = każda produkcja stosowana jedynie do pasującego węzła o najniższym indeksie
        - dangling_edges:
            1 = wykonanie produkcji jest anulowane przy braku transformacji osadzenia dla chociaż 1 wiszącej krawędzi
            2 = usuwana jest każda wisząca krawędź bez transformacji osadzenia
            (Jeśli None, przyjmuje ustawienie z definicji produkcji/gramatyki: "forbid" -> 1, "delete" -> 2)
        """
        if selection_strategy not in (1, 2):
            raise ValueError("Parametr selection_strategy musi mieć wartość 1 (wszystkie węzły) lub 2 (najniższy indeks).")
        if dangling_edges is not None and dangling_edges not in (1, 2):
            raise ValueError("Parametr dangling_edges musi mieć wartość 1 (anuluj) lub 2 (usuń krawędź).")

        for prod_item in productions:
            # Pobranie obiektu Production z gramatyki T
            if isinstance(prod_item, str):
                if prod_item not in self._productions_map:
                    raise ValueError(f"Produkcja '{prod_item}' nie należy do gramatyki T ('{self.T.name}').")
                prod = self._productions_map[prod_item]
            elif isinstance(prod_item, Production):
                prod = prod_item
            else:
                raise TypeError("Elementy listy produkcji muszą być nazwami (str) lub obiektami Production.")

            # Ustalenie trybu obsługi wiszących krawędzi (1 lub 2)
            if dangling_edges is not None:
                effective_dangling = dangling_edges
            else:
                effective_dangling = 1 if prod.dangling_edges == "forbid" else 2

            # Wyszukanie pasujących podgrafów
            matches = self._find_matches(prod, effective_dangling)

            if not matches:
                print(
                    f"[INFO] Produkcja '{prod.name}' pominięta/anulowana "
                    f"(brak dopasowania lub brak reguły osadzenia przy opcji dangling_edges=1)."
                )
                continue

            # Strategia 2: tylko węzeł o najniższym indeksie
            if selection_strategy == self.SELECTION_MIN_INDEX:
                chosen_match = matches[0]
                print(f"--> Stosowanie '{prod.name}' [strategia=2: min_index] na węzłach {chosen_match}")
                self._apply_to_match(prod, chosen_match)
                self.History.append((prod, self.G.copy()))

            # Strategia 1: wszystkie pasujące węzły
            elif selection_strategy == self.SELECTION_ALL_NODES:
                selected_matches = []
                used_vertices: Set[int] = set()
                for m in matches:
                    m_nodes = set(m.values())
                    if not (m_nodes & used_vertices):
                        selected_matches.append(m)
                        used_vertices.update(m_nodes)

                applied_any = False
                for m in selected_matches:
                    # Przy opcji 1 upewniamy się, że dla danego węzła nie ma nieobsłużonej wiszącej krawędzi
                    if effective_dangling == self.DANGLING_FORBID and self._has_unhandled_dangling_edges(prod, m):
                        continue
                    self._apply_to_match(prod, m)
                    applied_any = True

                if applied_any:
                    print(
                        f"--> Stosowanie '{prod.name}' [strategia=1: wszystkie węzły] "
                        f"na dopasowaniach: {selected_matches}"
                    )
                    self.History.append((prod, self.G.copy()))

        return self.History