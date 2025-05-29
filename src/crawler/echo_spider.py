import argparse
import time
import os
import json
import difflib
from newspaper import Article

from search_engines import (
    search_duckduckgo, search_google_cse
)

from similarity.detector import is_match
from dotenv import load_dotenv

HEADERS = {"User-Agent": "Mozilla/5.0"}
OUTPUT_DIR = "data/crawled"
os.makedirs(OUTPUT_DIR, exist_ok=True)

def extract_article_text(url):
    try:
        article = Article(url)
        article.download()
        article.parse()
        return article.text
    except Exception as e:
        print(f"[!] Failed to extract from {url}: {e}")
        return None

def get_top_sentences(text, n=5, max_words=20):
    sentences = [s.strip() for s in text.split('.') if len(s.strip()) > 25]
    short_snippets = []

    for s in sentences[:n]:
        s = s.replace("\"", "").replace("“", "").replace("”", "").replace("’", "'").replace("‘", "'")
        words = s.split()
        if len(words) > max_words:
            snippet = ' '.join(words[:max_words])
        else:
            snippet = ' '.join(words)
        short_snippets.append(f'"{snippet}"')

    return short_snippets

def resolve_engine(engine_name, query, config):
    if engine_name == "duckduckgo":
        return search_duckduckgo(query)
    elif engine_name == "google":
        return search_google_cse(query, config["GOOGLE_API_KEY"], config["GOOGLE_CSE_ID"])
    else:
        raise ValueError(f"Unknown search engine: {engine_name}")

def crawl_and_compare(seed_url, engine, config, threshold=0.80, delay=2):
    print(f"[*] Extracting seed content from: {seed_url}")
    seed_text = extract_article_text(seed_url)
    if not seed_text:
        print("[!] Could not extract seed content. Exiting.")
        return

    key_sentences = get_top_sentences(seed_text)
    print(f"[*] Generated {len(key_sentences)} search queries")

    found_matches = []

    for sent in key_sentences:
        print(f"[+] Searching with {engine}: {sent}")
        results = resolve_engine(engine, sent, config)
        print(f"[+] Found {len(results)} results")
        time.sleep(delay)

        for url in results:
            print(f"    - {url}")
            if seed_url in url:
                continue
            candidate_text = extract_article_text(url)
            if not candidate_text or len(candidate_text) < 100:
                continue

            match, score = is_match(seed_text, candidate_text, threshold=args.threshold)

            if match:
                print(f"[✓] Match found: {url} (similarity={score:.2f})")
                found_matches.append({
                    "source": url,
                    "similarity": score,
                    "snippet": candidate_text[:500]
                })
            time.sleep(delay)

    out_file = os.path.join(OUTPUT_DIR, f"matches_{engine}.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(found_matches, f, indent=2, ensure_ascii=False)
    print(f"[*] Saved {len(found_matches)} matches to {out_file}")


if __name__ == "__main__":

    load_dotenv()

    parser = argparse.ArgumentParser()
    parser.add_argument("url", help="Seed URL to trace")
    parser.add_argument("--engine", choices=["duckduckgo", "google"], default="duckduckgo")
    parser.add_argument("--threshold", type=float, default=0.80, help="Similarity threshold for matches")
    parser.add_argument("--delay", type=int, default=2, help="Delay in seconds between each query and match check")
    args = parser.parse_args()

    config = {
        "GOOGLE_API_KEY": os.getenv("GOOGLE_API_KEY"),
        "GOOGLE_CSE_ID": os.getenv("GOOGLE_CSE_ID")
    }

    crawl_and_compare(args.url, args.engine, config, threshold=args.threshold, delay=args.delay)
