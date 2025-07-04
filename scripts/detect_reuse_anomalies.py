#!/usr/bin/env python3
"""Detects content reuse anomalies by analyzing content hash patterns across domains."""

import json
import os
import argparse
from collections import defaultdict
from typing import Dict, List, Any


def load_json_file(file_path: str) -> Dict[str, Any]:
    """Load JSON data from a file."""
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json_file(data: Any, file_path: str) -> None:
    """Save data to a JSON file, creating parent directories if needed."""
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def detect_anomalies(reuse_map: Dict[str, Any], domain_labels: Dict[str, str]) -> List[Dict[str, Any]]:
    """Analyze content reuse patterns and detect anomalies."""
    anomalies = []

    for content_hash, group in reuse_map.items():
        sources = group.get("sources", [])

        label_groups = defaultdict(list)
        for item in sources:
            domain = item["domain"]
            label = domain_labels.get(domain, "unclassified")
            label_groups[label].append(domain)

        labels_used = list(label_groups.keys())

        anomaly_info = {
            "content_hash": content_hash,
            "reused_on": [
                {"domain": item["domain"], "label": domain_labels.get(item["domain"], "unclassified")}
                for item in sources
            ]
        }

        if len(sources) >= 2:
            anomalies.append({**anomaly_info, "issue": "High frequency reuse"})
        elif len(labels_used) >= 2:
            anomalies.append({**anomaly_info, "issue": "Cross-ideological reuse"})
        elif (all(domain_labels.get(item["domain"], "unclassified") == "unclassified" for item in sources)
              and len(sources) >= 3):
            anomalies.append({**anomaly_info, "issue": "Unclassified cluster reuse"})

    return anomalies


def main(input_path: str, labels_path: str, output_path: str) -> None:
    """Main execution function that loads data, detects anomalies, and saves results."""
    try:
        reuse_map = load_json_file(input_path)
        domain_labels = load_json_file(labels_path)
        anomalies = detect_anomalies(reuse_map, domain_labels)
        save_json_file(anomalies, output_path)
        print(f"[✓] Found {len(anomalies)} suspicious reuse cases. Saved to {output_path}")
    except Exception as e:
        print(f"[✗] Error processing files: {e}")
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Detect content reuse anomalies across domains.")
    parser.add_argument(
        "--input-path",
        default="data/analysis/reuse_map.json",
        help="Path to reuse map JSON file (default: data/analysis/reuse_map.json)"
    )
    parser.add_argument(
        "--labels-path",
        default="data/output/new_source_labels.json",
        help="Path to domain labels JSON file (default: data/output/new_source_labels.json)"
    )
    parser.add_argument(
        "--output-path",
        default="data/analysis/reuse_anomalies.json",
        help="Output path for anomalies JSON (default: data/analysis/reuse_anomalies.json)"
    )

    args = parser.parse_args()
    main(args.input_path, args.labels_path, args.output_path)