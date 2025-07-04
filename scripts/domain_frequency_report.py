#!/usr/bin/env python3
"""Analyzes domain frequency from crawled JSON data."""

import os
import json
from collections import Counter
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


def main(input_dir: str, output_path: str) -> None:
    """Main function to process crawled data and generate report."""
    print(f"[*] Analyzing domain frequency in {input_dir}...")
    domain_counts = load_labeled_urls(input_dir)
    save_report(domain_counts, output_path)
    print(f"[✓] Saved domain frequency report to {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Analyze domain frequency from crawled data.")
    parser.add_argument(
        "--input-dir",
        default="data/output",
        help="Directory containing crawled JSON files (default: data/output)"
    )
    parser.add_argument(
        "--output-path",
        default="data/output/domain_frequency_report.json",
        help="Output file path (default: data/output/domain_frequency_report.json)"
    )

    args = parser.parse_args()
    main(args.input_dir, args.output_path)