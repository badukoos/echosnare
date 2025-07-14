#!/usr/bin/env python3
"""
Generate domain labels from crawl data and existing labels.
Creates a new labels file with domains from crawl data and their classifications.
"""

import json
import sys
import argparse
from pathlib import Path
from typing import Dict, Set, Any
import tldextract


class DomainLabelGenerator:
    def __init__(self, known_labels: Dict[str, str]):
        self.known_labels = known_labels
        self.unclassified_domains: Set[str] = set()


    @staticmethod
    def extract_domain(url: str) -> str:
        """Extract registered domain from URL."""
        try:
            extracted = tldextract.extract(url)
            return f"{extracted.domain}.{extracted.suffix}"
        except Exception as e:
            raise ValueError(f"Failed to extract domain from URL: {url} - {e}")


    def process_crawl_data(self, matches: list) -> Dict[str, str]:
        """Process crawl data and generate domain labels."""
        domains = set()
        for entry in matches:
            url = entry.get("source") or entry.get("url")
            if url:
                try:
                    domain = self.extract_domain(url)
                    domains.add(domain)
                except ValueError as e:
                    print(f"[!] {e}", file=sys.stderr)

        enriched = {}
        for domain in sorted(domains):
            label = self.known_labels.get(domain, "unclassified")
            enriched[domain] = label
            if label == "unclassified":
                self.unclassified_domains.add(domain)

        return enriched


    def report_unclassified(self) -> None:
        """Print report about unclassified domains."""
        if not self.unclassified_domains:
            return

        print(f"\n[!] Found {len(self.unclassified_domains)} unclassified domains:")
        for domain in sorted(self.unclassified_domains)[:10]:
            print(f"  - {domain}")
        if len(self.unclassified_domains) > 10:
            print(f"  ... and {len(self.unclassified_domains) - 10} more")


def load_json_file(path: Path) -> Any:
    """Load JSON data from file with validation."""
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    if not path.is_file():
        raise ValueError(f"Path is not a file: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json_file(data: Any, path: Path) -> None:
    """Save data to JSON file with directory creation."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def main():

    DEFAULT_LABELS_PATH = "data/config/source_labels.json"
    DEFAULT_OUTPUT_PATH = "data/output/new_source_labels.json"

    parser = argparse.ArgumentParser(
        description="Generate domain labels from crawl data and existing labels",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        "--input-path",
        type=Path,
        required=True,
        help="Path to crawl output JSON file (e.g. data/crawled/matches_google.json)"
    )
    parser.add_argument(
        "--labels-path",
        type=Path,
        default=DEFAULT_LABELS_PATH,
        help="Path to existing labels JSON file"
    )
    parser.add_argument(
        "--output-path",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="Path for output new labels JSON file"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show detailed processing information"
    )

    args = parser.parse_args()

    try:
        print(f"[*] Loading crawl data from: {args.input_path}")
        matches = load_json_file(args.input_path)

        print(f"[*] Loading existing labels from: {args.labels_path}")
        known_labels = load_json_file(args.labels_path)

        generator = DomainLabelGenerator(known_labels)
        enriched_labels = generator.process_crawl_data(matches)

        print(f"\n[*] Saving new labels to: {args.output_path}")
        save_json_file(enriched_labels, args.output_path)

        generator.report_unclassified()
        print(f"\n[✓] Generated {len(enriched_labels)} labeled domains at {args.output_path}")

    except Exception as e:
        print(f"\n[✗] Error: {e}", file=sys.stderr)
        if args.verbose:
            print("Stack trace:", file=sys.stderr)
            raise
        sys.exit(1)


if __name__ == "__main__":
    main()
