import os
import json
import hashlib
from urllib.parse import urlparse
from glob import glob

INPUT_DIR = "data/output"
OUTPUT_PATH = "data/analysis/reuse_map.json"

os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)

def get_domain(url):
    try:
        return urlparse(url).netloc.replace("www.", "")
    except:
        return ""

def hash_text(text):
    return hashlib.sha256(text[:1000].encode("utf-8")).hexdigest()

def process_crawled_files():
    reuse_map = {}

    for path in glob(os.path.join(INPUT_DIR, "matches_*_labeled.json")):
        with open(path, encoding="utf-8") as f:
            entries = json.load(f)

        for entry in entries:
            snippet = entry.get("snippet", "")
            if not snippet.strip():
                continue

            h = hash_text(snippet)
            domain = get_domain(entry["source"])

            if h not in reuse_map:
                reuse_map[h] = {
                    "representative_snippet": snippet[:200],
                    "sources": []
                }

            reuse_map[h]["sources"].append({
                "domain": domain,
                "url": entry["source"],
                "label": entry.get("label", "unclassified"),
                "crawl_file": os.path.basename(path),
                "snippet": snippet[:1000]
            })

    return reuse_map

def main():
    reuse_data = process_crawled_files()
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(reuse_data, f, indent=2, ensure_ascii=False)
    print(f"[✓] Saved reuse map with {len(reuse_data)} unique content hashes to {OUTPUT_PATH}")

if __name__ == "__main__":
    main()
