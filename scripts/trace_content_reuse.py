#!/usr/bin/env python3
"""
Analyze content reuse across crawled documents by creating a map of content hashes to sources.
"""

import json
import hashlib
import argparse
import sys
from pathlib import Path
from urllib.parse import urlparse
from typing import Dict, List, Any
from glob import glob

class ContentReuseAnalyzer:
    def __init__(self, input_dir: str, output_path: str):
        self.input_dir = Path(input_dir)
        self.output_path = Path(output_path)
        self.output_path.parent.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def normalize_domain(url: str) -> str:
        """Extract and normalize domain from URL."""
        try:
            netloc = urlparse(url).netloc.lower()
            return netloc[4:] if netloc.startswith("www.") else netloc
        except (ValueError, AttributeError):
            return ""

    @staticmethod
    def generate_content_hash(text: str) -> str:
        """Generate SHA256 hash of text content."""
        return hashlib.sha256(text[:1000].encode("utf-8")).hexdigest()

    def process_file(self, file_path: Path) -> List[Dict[str, Any]]:
        """Process a single crawled file and extract entries."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            print(f"[!] Error processing {file_path.name}: {e}")
            return []

    def build_reuse_map(self) -> Dict[str, Dict[str, Any]]:
        """Build a map of content hashes to their sources."""
        reuse_map = {}
        file_pattern = self.input_dir / "matches_*_labeled.json"

        for file_path in glob(str(file_pattern)):
            entries = self.process_file(Path(file_path))
            if not entries:
                continue

            for entry in entries:
                snippet = entry.get("snippet", "").strip()
                if not snippet:
                    continue

                content_hash = self.generate_content_hash(snippet)
                domain = self.normalize_domain(entry["source"])

                if content_hash not in reuse_map:
                    reuse_map[content_hash] = {
                        "representative_snippet": snippet[:200],
                        "sources": []
                    }

                reuse_map[content_hash]["sources"].append({
                    "domain": domain,
                    "url": entry["source"],
                    "label": entry.get("label", "unclassified"),
                    "crawl_file": Path(file_path).name,
                    "snippet": snippet[:1000]
                })

        return reuse_map

    def save_results(self, reuse_data: Dict[str, Any]) -> None:
        """Save the reuse map to JSON file."""
        with open(self.output_path, "w", encoding="utf-8") as f:
            json.dump(reuse_data, f, indent=2, ensure_ascii=False)

    def run(self) -> None:
        """Execute the analysis pipeline."""
        print(f"[*] Analyzing content reuse in {self.input_dir}")
        reuse_data = self.build_reuse_map()
        self.save_results(reuse_data)
        print(f"[✓] Saved reuse map with {len(reuse_data)} unique content hashes to {self.output_path}")

def main():
    DEFAULT_INPUT_DIR = "data/output"
    DEFAULT_OUTPUT_PATH = "data/analysis/reuse_map.json"

    parser = argparse.ArgumentParser(
        description="Analyze content reuse across crawled documents",
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
        help="Path for output JSON file"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show detailed processing information"
    )

    args = parser.parse_args()

    try:
        analyzer = ContentReuseAnalyzer(args.input_dir, args.output_path)
        analyzer.run()
    except Exception as e:
        print(f"\n[✗] Error: {e}", file=sys.stderr)
        if args.verbose:
            print("\nStack trace:", file=sys.stderr)
            raise
        sys.exit(1)

if __name__ == "__main__":
    main()