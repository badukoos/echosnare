#!/usr/bin/env python3
"""Detects content reuse anomalies by analyzing content hash patterns across domains."""

import json
import os
import argparse
from collections import defaultdict
from pathlib import Path
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


def main():

    DEFAULT_INPUT_PATH = "data/analysis/reuse_map.json"
    DEFAULT_LABELS_PATH = "data/output/new_source_labels.json"
    DEFAULT_OUTPUT_PATH = "data/analysis/reuse_anomalies.json"

    parser = argparse.ArgumentParser(
        description="Detect content reuse anomalies across domains",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        "--input-path",
        type=Path,
        default=DEFAULT_INPUT_PATH,
        help="Path to reuse map JSON file"
    )
    parser.add_argument(
        "--labels-path",
        type=Path,
        default=DEFAULT_LABELS_PATH,
        help="Path to new source labels JSON file"
    )
    parser.add_argument(
        "--output-path",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="Output path for anomalies JSON file"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show detailed processing information"
    )

    args = parser.parse_args()

    try:
        reuse_map = load_json_file(args.input_path)
        domain_labels = load_json_file(args.labels_path)
        anomalies = detect_anomalies(reuse_map, domain_labels)
        save_json_file(anomalies, args.output_path)
        print(f"[✓] Found {len(anomalies)} suspicious reuse cases. Saved to {args.output_path}")
    except Exception as e:
        print(f"[✗] Error: {e}", file=sys.stderr)
        if args.verbose:
            print("Stack trace:", file=sys.stderr)
            raise
        sys.exit(1)


if __name__ == "__main__":
    main()