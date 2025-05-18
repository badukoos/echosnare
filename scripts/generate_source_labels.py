import json
import sys
import tldextract

def extract_domain(url):
    extracted = tldextract.extract(url)
    return f"{extracted.domain}.{extracted.suffix}"

def main(matches_path, labels_path, output_path):
    with open(matches_path, "r", encoding="utf-8") as f:
        matches = json.load(f)

    with open(labels_path, "r", encoding="utf-8") as f:
        known_labels = json.load(f)

    domains = set()
    for entry in matches:
        url = entry.get("source") or entry.get("url")
        if url:
            domain = extract_domain(url)
            domains.add(domain)

    enriched = {}
    for domain in sorted(domains):
        enriched[domain] = known_labels.get(domain, "unclassified")

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(enriched, f, indent=2)

    print(f"[✓] Generated {len(enriched)} labeled entries at {output_path}")

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python generate_source_labels.py <crawl_output.json> <existing_labels.json> <output_new_labels.json>")
        sys.exit(1)

    main(sys.argv[1], sys.argv[2], sys.argv[3])
