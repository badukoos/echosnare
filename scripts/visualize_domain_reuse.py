#!/usr/bin/env python3
"""
Visualize domain reuse anomalies as an interactive network graph.
"""

import json
import argparse
import sys
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, DefaultDict, Tuple

import networkx as nx
from pyvis.network import Network

class DomainGraphVisualizer:
    DEFAULT_COLOR_MAP = {
        "credible": "#4CAF50",  # green
        "state-sponsored": "#F44336",  # red
        "conspiratorial": "#FF9800",  # orange
        "unclassified": "#9E9E9E"  # gray
    }

    def __init__(self, input_path: str, labels_path: str, output_path: str):
        self.input_path = Path(input_path)
        self.labels_path = Path(labels_path)
        self.output_path = Path(output_path)
        self.output_path.parent.mkdir(parents=True, exist_ok=True)

    def load_data(self) -> Tuple[List[Dict], Dict[str, str]]:
        """Load anomalies and labels data with validation."""
        try:
            with open(self.input_path, "r", encoding="utf-8") as f:
                anomalies = json.load(f)
            with open(self.labels_path, "r", encoding="utf-8") as f:
                labels = json.load(f)
            return anomalies, labels
        except (FileNotFoundError, json.JSONDecodeError) as e:
            raise RuntimeError(f"Failed to load data: {e}")

    def build_network_graph(self, anomalies: List[Dict]) -> nx.Graph:
        """Construct network graph from anomalies data."""
        G = nx.Graph()
        grouped: DefaultDict[str, List] = defaultdict(list)

        for entry in anomalies:
            grouped[entry["issue"]].append(entry)

        for cluster in grouped.values():
            for anomaly in cluster:
                domains = [d["domain"] for d in anomaly["reused_on"]]
                for i, domain in enumerate(domains):
                    if not G.has_node(domain):
                        G.add_node(domain)
                    for j in range(i + 1, len(domains)):
                        G.add_edge(domain, domains[j])
        return G

    def visualize_graph(self, G: nx.Graph, labels: Dict[str, str]) -> None:
        """Generate interactive visualization using PyVis."""
        net = Network(
            notebook=False,
            height="750px",
            width="100%",
            bgcolor="#1e1e1e",
            font_color="white",
            select_menu=True,
            cdn_resources="in_line"
        )

        for node in G.nodes:
            label_type = labels.get(node, "unclassified")
            net.add_node(
                node,
                label=node,
                color=self.DEFAULT_COLOR_MAP.get(label_type, "#9E9E9E"),
                title=f"{node}\nType: {label_type}",
                size=15
            )

        for edge in G.edges:
            net.add_edge(edge[0], edge[1], width=0.5)

        net.set_options("""
        {
            "nodes": {
                "borderWidth": 2,
                "shadow": true
            },
            "edges": {
                "smooth": false,
                "color": {
                    "inherit": true
                }
            },
            "physics": {
                "forceAtlas2Based": {
                    "gravitationalConstant": -50,
                    "centralGravity": 0.01,
                    "springLength": 100,
                    "springConstant": 0.08
                },
                "minVelocity": 0.75,
                "solver": "forceAtlas2Based",
                "timestep": 0.5,
                "stabilization": {
                    "enabled": true,
                    "iterations": 1000
                }
            }
        }
        """)

        net.save_graph(str(self.output_path))

    def run(self) -> None:
        """Execute the visualization pipeline."""
        print(f"[*] Loading data from {self.input_path}")
        anomalies, labels = self.load_data()

        print("[*] Building network graph")
        graph = self.build_network_graph(anomalies)

        print(f"[*] Generating visualization at {self.output_path}")
        self.visualize_graph(graph, labels)

        print(f"[✓] Successfully saved visualization to {self.output_path}")

def main():
    DEFAULT_INPUT_PATH = "data/analysis/reuse_anomalies.json"
    DEFAULT_LABELS_PATH = "data/output/new_source_labels.json"
    DEFAULT_OUTPUT_PATH = "data/analysis/domain_reuse_graph.html"

    parser = argparse.ArgumentParser(
        description="Visualize domain reuse patterns as interactive network graphs",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        "--input-path",
        type=Path,
        default=DEFAULT_INPUT_PATH,
        help="Path to anomalies JSON file"
    )
    parser.add_argument(
        "--labels-path",
        type=Path,
        default=DEFAULT_LABELS_PATH,
        help="Path to domain labels JSON file"
    )
    parser.add_argument(
        "--output-path",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="Output path for HTML visualization"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show detailed processing information"
    )

    args = parser.parse_args()

    try:
        visualizer = DomainGraphVisualizer(
            args.input_path,
            args.labels_path,
            args.output_path
        )
        visualizer.run()
    except Exception as e:
        print(f"[✗] Error: {e}", file=sys.stderr)
        if args.verbose:
            print("Stack trace:", file=sys.stderr)
            raise
        sys.exit(1)

if __name__ == "__main__":
    main()