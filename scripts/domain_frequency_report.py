#!/usr/bin/env python3
"""Analyzes domain frequency from crawled JSON data."""

import os
import json
from collections import Counter
from pathlib import Path
import tldextract
import argparse

def extract_domain(url: str) -> str:
    """Extract domain from URL using tldextract."""
    try:
        extracted = tldextract.extract(url)
        return f"{extracted.domain}.{extracted.suffix}"
    except Exception:
        return None

def load_labeled_urls(directory: str) -> Counter:
    """Load and count domains from all JSON files that ends with 'labled'"""
    domain_counter = Counter()

    for filename in os.listdir(directory):
        if not filename.endswith(".json") or "labeled" in filename:
            continue

        path = os.path.join(directory, filename)
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError:
            print(f"[!] Skipping {filename} due to JSON error")
            continue

        for item in data:
            url = None
            if isinstance(item, dict):
                url = item.get("source") or item.get("url")
            elif isinstance(item, str):
                url = item

            if url:
                domain = extract_domain(url)
                if domain:
                    domain_counter[domain] += 1

    return domain_counter

def save_report(counter: Counter, output_path: str) -> None:
    """Save domain frequency report as JSON."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(dict(counter.most_common()), f, indent=2)

def main():
    DEFAULT_INPUT_DIR="data/output"
    DEFAULT_OUTPUT_PATH="data/output/domain_frequency_report.json"

    parser = argparse.ArgumentParser(
        description="Analyze domain frequency from crawled data",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=DEFAULT_INPUT_DIR,
        help="Directory containing crawled JSON files"
    )
    parser.add_argument(
        "--output-path",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="Output JSON file path for the generated report"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show detailed processing information"
    )

    args = parser.parse_args()

    try:
        print(f"[*] Analyzing domain frequency in {args.input_dir}...")
        domain_counts = load_labeled_urls(args.input_dir)
        save_report(domain_counts, args.output_path)
        print(f"[✓] Saved domain frequency report to {args.output_path}")
    except Exception as e:
        print(f"[✗] Error: {e}", file=sys.stderr)
        if args.verbose:
            print("Stack trace:", file=sys.stderr)
            raise
        sys.exit(1)

if __name__ == "__main__":
    main()