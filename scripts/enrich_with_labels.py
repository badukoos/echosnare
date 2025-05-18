import json
import os
import sys
from urllib.parse import urlparse
import tldextract

def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_json(data, path):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def extract_domain(url):
    extracted = tldextract.extract(url)
    return f"{extracted.domain}.{extracted.suffix}"

def enrich_with_labels(crawl_file, labels_file, output_file):
    print(f"[+] Loading crawl data from: {crawl_file}")
    crawl_data = load_json(crawl_file)

    print(f"[+] Loading source labels from: {labels_file}")
    source_labels = load_json(labels_file)

    unmatched_domains = set()

    for entry in crawl_data:
        url = entry.get("source") or entry.get("url")
        if not url:
            entry["label"] = "unclassified"
            continue

        domain = extract_domain(url)
        label = source_labels.get(domain)

        if not label:
            label = "unclassified"
            unmatched_domains.add(domain)

        entry["label"] = label

    if unmatched_domains:
        print(f"[!] Warning: {len(unmatched_domains)} unmatched domains (showing up to 10):")
        for d in list(unmatched_domains)[:10]:
            print(f"    - {d}")

    print(f"[+] Saving enriched data to: {output_file}")
    save_json(crawl_data, output_file)
    print("[✓] Done.")

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python enrich_with_labels.py <crawl_output.json> <source_labels.json> <output_file.json>")
        sys.exit(1)

    crawl_file = sys.argv[1]
    labels_file = sys.argv[2]
    output_file = sys.argv[3]

    enrich_with_labels(crawl_file, labels_file, output_file)
