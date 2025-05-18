import os
import json
from urllib.parse import urlparse
from collections import Counter
import tldextract

CRAWLED_DIR = "data/output"

def extract_domain(url):
    try:
        extracted = tldextract.extract(url)
        return f"{extracted.domain}.{extracted.suffix}"
    except Exception:
        return None

def load_all_urls_from_crawls(directory):
    domain_counter = Counter()

    for filename in os.listdir(directory):
        if not filename.endswith(".json") or "labeled" in filename:
            continue
        path = os.path.join(directory, filename)
        with open(path, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                print(f"[!] Skipping {filename} due to JSON error")
                continue

            for item in data:
                if isinstance(item, dict):
                    url = item.get("source") or item.get("url")
                elif isinstance(item, str):
                    url = item
                else:
                    continue

                if url:
                    domain = extract_domain(url)
                    if domain:
                        domain_counter[domain] += 1

    return domain_counter

def save_report(counter, output_path):
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(dict(counter.most_common()), f, indent=2)

if __name__ == "__main__":
    print(f"[*] Analyzing domain frequency in {CRAWLED_DIR}...")
    domain_counts = load_all_urls_from_crawls(CRAWLED_DIR)
    OUTPUT_DIR = "data/output"
    output_file = os.path.join(OUTPUT_DIR, "domain_frequency_report.json")
    save_report(domain_counts, output_file)
    print(f"[✓] Saved domain frequency report to {output_file}")
