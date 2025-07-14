#!/usr/bin/env python3
"""Enrich crawl data with domain labels."""

import json
import os
import sys
import argparse
from pathlib import Path
from typing import Dict, List, Set, Any
import tldextract


def load_json(path: str) -> Any:
    """Load JSON data from file."""
    path_obj = Path(path)
    if not path_obj.exists():
        raise FileNotFoundError(f"Input file not found: {path}")
    if not path_obj.is_file():
        raise ValueError(f"Path is not a file: {path}")
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_json(data: Any, path: str) -> None:
    """Save data to JSON file."""
    path_obj = Path(path)
    try:
        path_obj.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except PermissionError:
        raise PermissionError(f"Cannot write to output file: {path}")
    except Exception as e:
        raise Exception(f"Failed to save output: {e}")


def extract_domain(url: str) -> str:
    """Extract registered domain from URL."""
    try:
        extracted = tldextract.extract(url)
        return f"{extracted.domain}.{extracted.suffix}"
    except Exception as e:
        raise ValueError(f"Failed to extract domain from URL: {url} - {e}")


class DataEnricher:
    def __init__(self, labels: Dict[str, str]):
        self.labels = labels
        self.unmatched_domains: Set[str] = set()


    def process_entry(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        """Add label to a single crawl entry."""
        try:
            url = entry.get("source") or entry.get("url")
            if not url:
                entry["label"] = "unclassified"
                return entry

            domain = extract_domain(url)
            label = self.labels.get(domain, "unclassified")

            if label == "unclassified":
                self.unmatched_domains.add(domain)

            entry["label"] = label
            return entry
        except Exception as e:
            print(f"[!] Error processing entry: {e}")
            entry["label"] = "error"
            return entry


    def report_unmatched(self) -> None:
        """Print warning about unmatched domains."""
        if not self.unmatched_domains:
            return

        print(f"\n[!] Warning: Found {len(self.unmatched_domains)} domains with 'unclassified' labels")
        print("Top 10 unmatched domains:")
        for domain in sorted(list(self.unmatched_domains))[:10]:
            print(f"  - {domain}")
        print("\nConsider adding these to your source labels file for better classification in the future.")


def enrich_with_labels(input_path: str, labels_path: str, output_path: str) -> None:
    """Main enrichment workflow."""
    try:
        # Validate input files exist
        if not Path(input_path).exists():
            raise FileNotFoundError(f"Crawl data file not found: {input_path}")
        if not Path(labels_path).exists():
            raise FileNotFoundError(f"Labels file not found: {labels_path}")

        print(f"[*] Loading crawl data from: {input_path}")
        crawl_data = load_json(input_path)

        print(f"[*] Loading source labels from: {labels_path}")
        source_labels = load_json(labels_path)

        print("\n[*] Processing entries...")
        enricher = DataEnricher(source_labels)
        crawl_data = [enricher.process_entry(entry) for entry in crawl_data]

        enricher.report_unmatched()

        print(f"\n[*] Saving enriched data to: {output_path}")
        save_json(crawl_data, output_path)
        print("[✓] Enrichment completed successfully")

    except Exception as e:
        raise Exception(f"Enrichment failed: {e}")


def main():

    DEFAULT_LABELS_PATH = "data/config/source_labels.json"

    parser = argparse.ArgumentParser(
        description='Enrich crawl data with domain labels',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        '--input-path',
        required=True,
        help='Path to crawl data JSON file (e.g. data/crawled/matches_google.json)'
    )
    parser.add_argument(
        '--labels-path',
        default=DEFAULT_LABELS_PATH,
        help='Path to domain labels JSON file'
    )
    parser.add_argument(
        '--output-path',
        required=True,
        help='Path for output JSON file (e.g. data/output/matches_google_labeled.json)'
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show detailed processing information"
    )

    args = parser.parse_args()

    try:
        enrich_with_labels(args.input_path, args.labels_path, args.output_path)
    except Exception as e:
        print(f"\n[✗] Error: {e}", file=sys.stderr)
        if args.verbose:
            print("Stack trace:", file=sys.stderr)
            raise
        sys.exit(1)


if __name__ == "__main__":
    main()