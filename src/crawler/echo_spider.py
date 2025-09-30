#!/usr/bin/env python3
"""
This script accepts a seed url and then
  - extracts article text from the seed url
  - generates short sentences for search then searches on the chosen engine
  - fetches candidate articles and checks text similarity to find likely echoes and reposts
"""
import argparse
import time
import os
import json
from urllib.parse import urlparse

from newspaper import Article
from dotenv import load_dotenv

from search_engines import (
    search_duckduckgo,
    search_google_cse,
    search_gdelt_variants,
)

from similarity.detector import is_match

DEFAULTS: dict = {
    "output_dir": "data/crawled",
    # Default number of sentences and max words
    "get_top_sentences": {"n": 5, "max_words": 20},
    "similarity_threshold": 0.80,
    "delay_seconds": 2,
    # Default limit: max number of urls collected per search
    "gdelt": {
        "limit": 10,
        "timespan": os.getenv("GDELT_TIMESPAN", "30d"),
    },
}

os.makedirs(DEFAULTS["output_dir"], exist_ok=True)


def extract_article_text(url: str) -> str | None:
    """Download and parse newpaper article"""
    try:
        article = Article(url)
        article.download()
        article.parse()
        return article.text
    except Exception as e:
        print(f"[!] Failed to extract from {url}: {e}")
        return None


def get_top_sentences(text: str, n: int | None = None, max_words: int | None = None) -> list[str]:
    """Produce snippets to be used as search queries"""
    cfg = DEFAULTS["get_top_sentences"]
    n = cfg["n"] if n is None else n
    max_words = cfg["max_words"] if max_words is None else max_words

    # Keep "long enough" fragments so we avoid titles/captions/etc
    sentences = [s.strip() for s in text.split('.') if len(s.strip()) > 25]

    short_snippets: list[str] = []
    for s in sentences[:n]:
        # Replace quotes to avoid nested-quote issues in search queries
        s = (
            s.replace('"', "")
             .replace("“", "")
             .replace("”", "")
             .replace("’", "'")
             .replace("‘", "'")
        )
        words = s.split()
        snippet = ' '.join(words[:max_words]) if len(words) > max_words else ' '.join(words)
        short_snippets.append(f'"{snippet}"')

    return short_snippets


def _domain_of(u: str) -> str:
    """Return normalized netloc from a URL that is then used to exclude seed domain"""
    try:
        d = urlparse(u).netloc.lower()
        return d[4:] if d.startswith("www.") else d
    except Exception:
        return ""


def crawl_and_compare(
    seed_url: str,
    engine: str,
    config: dict,
    *,
    threshold: float | None = None,
    delay: int | None = None,
    gdelt_start: str | None = None,
    gdelt_end: str | None = None,
    gdelt_timespan: str | None = None,
    gdelt_limit: int | None = None,
) -> None:
    """
    Various things done here:
      - extract seed text
      - create query snippets
      - search each snippet
      - fetch & compare candidate texts against the seed text
      - save matches as JSON
    """
    # Resolve configuration defaults
    threshold = DEFAULTS["similarity_threshold"] if threshold is None else threshold
    delay = DEFAULTS["delay_seconds"] if delay is None else delay

    # GDELT specific defaults
    gd_cfg = DEFAULTS["gdelt"]
    gdelt_timespan = gd_cfg["timespan"] if gdelt_timespan is None else gdelt_timespan
    gdelt_limit = gd_cfg["limit"] if gdelt_limit is None else gdelt_limit

    print(f"[*] Extracting seed content from: {seed_url}")
    seed_text = extract_article_text(seed_url)
    if not seed_text:
        print("[!] Could not extract seed content. Exiting.")
        return

    key_sentences = get_top_sentences(seed_text)
    print(f"[*] Generated {len(key_sentences)} search queries")

    found_matches: list[dict] = []

    seed_domain = _domain_of(seed_url)

    for sent in key_sentences:
        print(f"[+] Searching with {engine}: {sent}")

        if engine == "gdelt":
            q = sent.strip('"')  # GDELT prefers unquoted bag/NEAR terms
            results = search_gdelt_variants(
                q,
                exclude_domain=seed_domain,
                limit=gdelt_limit,
                start=gdelt_start,
                end=gdelt_end,
                timespan=gdelt_timespan,
            )
        elif engine == "duckduckgo":
            results = search_duckduckgo(sent)
        else:
            results = search_google_cse(sent, config["GOOGLE_API_KEY"], config["GOOGLE_CSE_ID"])

        print(f"[+] Found {len(results)} results")
        time.sleep(delay)

        for url in results:
            print(f"    - {url}")
            # Skip self-references back to the seed source.
            if seed_url in url:
                continue

            candidate_text = extract_article_text(url)
            if not candidate_text or len(candidate_text) < 100:
                # Very short articles are not worth comparing
                continue

            match, score = is_match(seed_text, candidate_text, threshold=threshold)

            if match:
                print(f"[✓] Match found: {url} (similarity={score:.2f})")
                found_matches.append(
                    {
                        "source": url,
                        "similarity": score,
                        "snippet": candidate_text[:500],
                    }
                )

            time.sleep(delay)

    out_file = os.path.join(DEFAULTS["output_dir"], f"matches_{engine}.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(found_matches, f, indent=2, ensure_ascii=False)
    print(f"[*] Saved {len(found_matches)} matches to {out_file}")


if __name__ == "__main__":

    load_dotenv()

    parser = argparse.ArgumentParser()
    parser.add_argument("url", help="Seed URL to trace")
    parser.add_argument("--engine", choices=["duckduckgo", "google", "gdelt"], default="gdelt")

    parser.add_argument("--gdelt-start", help="GDELT STARTDATETIME, should be YYYYMMDD or YYYYMMDDHHMMSS or YYYY-MM-DD")
    parser.add_argument("--gdelt-end", help="GDELT ENDDATETIME, should be YYYYMMDD or YYYYMMDDHHMMSS or YYYY-MM-DD")
    parser.add_argument("--gdelt-timespan", help="GDELT TIMESPAN (e.g., '7d', '30d', '1week', '3months'), ignored if start/end provided")
    parser.add_argument("--threshold", type=float, default=DEFAULTS["similarity_threshold"], help=f"Similarity threshold for matches (default: {DEFAULTS['similarity_threshold']})")
    parser.add_argument("--delay", type=int, default=DEFAULTS["delay_seconds"], help=f"Delay in seconds between each query and match check (default: {DEFAULTS['delay_seconds']})")
    args = parser.parse_args()

    # Get Google API keys stored in .env
    config = {
        "GOOGLE_API_KEY": os.getenv("GOOGLE_API_KEY"),
        "GOOGLE_CSE_ID": os.getenv("GOOGLE_CSE_ID"),
    }

    # GDELT specific parameters, ignored for other search options
    gd_start = args.gdelt_start if args.engine == "gdelt" else None
    gd_end = args.gdelt_end if args.engine == "gdelt" else None
    gd_span = args.gdelt_timespan if args.engine == "gdelt" else None

    crawl_and_compare(
        args.url,
        args.engine,
        config,
        threshold=args.threshold,
        delay=args.delay,
        gdelt_start=gd_start,
        gdelt_end=gd_end,
        gdelt_timespan=gd_span,
        gdelt_limit=DEFAULTS["gdelt"]["limit"],
    )
