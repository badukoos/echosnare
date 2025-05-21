import json
import os
import networkx as nx
from pyvis.network import Network
from collections import defaultdict

INPUT_PATH = "data/analysis/reuse_anomalies.json"
LABELS_PATH = "data/output/new_source_labels.json"
OUTPUT_PATH = "data/analysis/domain_reuse_graph.html"

def visualize():
    with open(INPUT_PATH, "r", encoding="utf-8") as f:
        anomalies = json.load(f)
    with open(LABELS_PATH, "r", encoding="utf-8") as f:
        labels = json.load(f)

    G = nx.Graph()
    color_map = {
        "credible": "green",
        "state-sponsored": "red",
        "conspiratorial": "orange",
        "unclassified": "gray"
    }

    grouped = defaultdict(list)
    for entry in anomalies:
        grouped[entry["issue"]].append(entry)

    for cluster in grouped.values():
        for anomaly in cluster:
            domains = [d["domain"] for d in anomaly["reused_on"]]
            for i in range(len(domains)):
                for j in range(i + 1, len(domains)):
                    G.add_edge(domains[i], domains[j])
                if not G.has_node(domains[i]):
                    G.add_node(domains[i])

    net = Network(notebook=False, height="750px", width="100%", bgcolor="#1e1e1e", font_color="white")

    for node in G.nodes:
        label = labels.get(node, "unclassified")
        net.add_node(node, label=node, color=color_map.get(label, "gray"))

    for edge in G.edges:
        net.add_edge(edge[0], edge[1])

    net.show_buttons(filter_=['physics'])
    net.write_html(OUTPUT_PATH)
    print(f"[✓] Saved visualization to {OUTPUT_PATH}")


if __name__ == "__main__":
    visualize()
