#!/usr/bin/env python3
"""Search helpers"""
import re
import requests
from bs4 import BeautifulSoup
from datetime import datetime

DEFAULTS: dict = {
    "headers": {"User-Agent": "Mozilla/5.0"},
    "duckduckgo": {"max_results": 10},
    "google": {"num": 10},
    "gdelt": {
        "limit": 10,
        "timespan": "30d",
        "timeout": 30,
    },
    "gdelt_query": {
        "near_k": 10,
        # Best to keep queries compact to reduce API errors
        "max_terms": 8,
        "sourcelang": "english",
    },
}

# Common stopwords that has to be stripped from queries
STOP = {
    "the","a","an","and","or","but","to","of","in","on","for","with","as","by",
    "is","are","was","were","be","been","being","that","this","it","its","at",
    "from","about","into","over","after","before","between","through","their",
    "has","have","had","today","yesterday","tomorrow","new","more"
}

# Allow list acronyms
ACRONYM_ALLOW = {"NATO", "UAE", "EU", "US", "UK", "UN"}


def search_duckduckgo(query: str, max_results: int | None = None, *, headers: dict | None = None) -> list[str]:
    """Lightweight HTML form search against DuckDuckGo's HTML endpoint"""
    results: list[str] = []
    max_results = DEFAULTS["duckduckgo"]["max_results"] if max_results is None else max_results
    headers = DEFAULTS["headers"] if headers is None else headers

    try:
        res = requests.post("https://html.duckduckgo.com/html/", data={"q": query}, headers=headers, timeout=30)
        soup = BeautifulSoup(res.text, "lxml")
        for a in soup.select("a.result__a"):
            href = a.get("href")
            if href:
                results.append(href)
            if len(results) >= max_results:
                break
    except Exception as e:
        print(f"[!] DuckDuckGo search failed: {e}")
    return results


def search_google_cse(query: str, api_key: str, cse_id: str, num: int | None = None) -> list[str]:
    """Google Custom Search API, requires API key & CSE ID"""
    num = DEFAULTS["google"]["num"] if num is None else num
    try:
        from googleapiclient.discovery import build
        service = build("customsearch", "v1", developerKey=api_key)
        res = service.cse().list(q=query, cx=cse_id, num=num).execute()
        return [item['link'] for item in res.get('items', [])]
    except Exception as e:
        print(f"[!] Google CSE failed: {e}")
        return []


def _normalize_text(s: str) -> str:
    """Normalize curly quotes to simpler ASCII-ish form"""
    return (
        s.replace("’", "'")
         .replace("“", '"')
         .replace("”", '"')
         .replace("\u00a0", " ")
         .strip()
    )


def _tokens(sentence: str) -> list[str]:
    """Tokenize a sentence into unique keywords while dropping stopwords and tiny tokens"""
    s = _normalize_text(sentence)
    # Start with alpha num, followed by 1+ of alpha num or a dash
    # (TODO: Check if dashes are valid, appears in split words)
    raw = re.findall(r"[A-Za-z0-9][A-Za-z0-9\-]{1,}", s)

    out: list[str] = []
    seen: set[str] = set()
    for t in raw:
        tl = t.lower()
        if tl in STOP:
            continue
        # Drop all < 3 char tokens unless whitelisted
        if len(t) < 3 and t.upper() not in ACRONYM_ALLOW:
            continue
        if tl not in seen:
            out.append(t)
            seen.add(tl)
    return out


def _quote(words: list[str]) -> str:
    """Return a phrase quoted for NEAR/phrase queries"""
    return f"\"{' '.join(words)}\""


def build_gdelt_queries(
    sentence: str,
    *,
    near_k: int | None = None,
    max_terms: int | None = None,
    sourcelang: str | None = None,
    exclude_domain: str | None = None,
) -> list[str]:
    """
    Build a small set of GDELT query variants from a sentence and return short de duplicated qury strings
    Notes: GDELT DOC API is picky about long/complex queries
      - Prefer up to `max_terms` tokens
      - Bias towards ProperCase and whitelisted acronyms first
      - Generate a NEAR variant, a short quoted phrase, and an AND-only bag-of-terms
    """
    qcfg = DEFAULTS["gdelt_query"]
    near_k = qcfg["near_k"] if near_k is None else near_k
    max_terms = qcfg["max_terms"] if max_terms is None else max_terms
    sourcelang = qcfg["sourcelang"] if sourcelang is None else sourcelang

    terms = _tokens(sentence)[:max_terms]
    if not terms:
        return []

    # Prefer named/acronym tokens first
    named = [t for t in terms if t[0].isupper() or t.isupper()]
    others = [t for t in terms if t not in named]
    core = (named + others)[:max_terms]

    head = core[:3]  # strongest 3 for NEAR/phrase
    tail = [t for t in core[3:] if len(t) >= 3][:3]  # additional terms

    filters: list[str] = []
    if sourcelang:
        filters.append(f"sourcelang:{sourcelang}")
    if exclude_domain:
        pass

    variants: list[str] = []

    # NEAR + AND
    if head:
        variants.append(f'near{near_k}:{_quote(head)} {" ".join(tail + filters)}'.strip())

    # short phrase + AND i.e no NEAR
    if len(head) >= 2:
        variants.append(f'{_quote(head[:2])} {" ".join(tail[:2] + filters)}'.strip())

    # bag of terms i.e AND only, no less than 3 char tokens
    variants.append(" ".join([t for t in core if len(t) >= 3] + filters).strip())

    # De-duplicate and drop empties
    seen: set[str] = set()
    clean: list[str] = []
    for q in variants:
        q = " ".join(q.split())
        if q and q not in seen:
            seen.add(q)
            clean.append(q)
    return clean


def _retry_fix_query(q: str, head_text: str) -> str | None:
    """Attempt small, surgical fixes when GDELT returns an HTML error page"""
    msg = head_text.lower()

    # Remove NEAR clause if it's flagged as invalid
    if "invalid near" in msg or "near search" in msg:
        q = re.sub(r'\bnear\d+:"[^"]+"\s*', '', q).strip()
        return q or None

    # Drop too-short tokens
    if "too short" in msg:
        toks = [t for t in q.split() if (t.startswith('"') and t.endswith('"')) or len(t) >= 3]
        q2 = " ".join(toks).strip()
        return q2 or None

    # wrap whole thing in quotes if not already quoted when there are "illefal chars"
    if "illegal character" in msg and not (q.startswith('"') and q.endswith('"')):
        return f"\"{q}\""

    return None


def _gdelt_fmt(dtobj: datetime | str) -> str:
    """Convert supported datetime-like inputs to GDELT's YYYYMMDDHHMMSS format"""
    if isinstance(dtobj, datetime):
        return dtobj.strftime("%Y%m%d%H%M%S")
    s = str(dtobj).strip()

    # YYYYMMDDHHMMSS
    if re.fullmatch(r"\d{14}", s):
        return s

    # YYYYMMDD
    if re.fullmatch(r"\d{8}", s):
        return s + "000000"

    # YYYY-MM-DD
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", s):
        return s.replace("-", "") + "000000"
    raise ValueError(f"Unsupported datetime format for GDELT: {dtobj!r}")


def search_gdelt_single(
    query: str,
    max_results: int | None = None,
    *,
    start: str | datetime | None = None,
    end: str | datetime | None = None,
    timespan: str | None = None,
    timeout: int | None = None,
) -> list[str]:
    """Single GDELT DOC API call for a given query. Returns list of articles, recent at teh top"""
    base = "https://api.gdeltproject.org/api/v2/doc/doc"
    max_results = DEFAULTS["gdelt"]["limit"] if max_results is None else max_results
    timespan = DEFAULTS["gdelt"]["timespan"] if timespan is None else timespan
    # HTTP timeout in seconds
    timeout = DEFAULTS["gdelt"]["timeout"] if timeout is None else timeout

    params = {
        "query": query,
        "mode": "artlist",
        "format": "json",
        "maxrecords": str(max(1, min(max_results, 250))),
        "sort": "datedesc",
    }

    # Prefer explicit window if provided else use timespan
    if start or end:
        if start:
            params["STARTDATETIME"] = _gdelt_fmt(start)
        if end:
            params["ENDDATETIME"] = _gdelt_fmt(end)
    else:
        params["timespan"] = timespan

    try:
        r = requests.get(base, params=params, timeout=timeout, headers=DEFAULTS["headers"])
        r.raise_for_status()
        ctype = (r.headers.get("content-type", "")).lower()
        if "application/json" not in ctype:
            # GDELT sometimes returns HTML with an error explanation. Try a tiny fix
            head = r.text[:240].replace("\n", " ")
            print(f"[!] GDELT non-JSON head: {head} ...")
            fixed = _retry_fix_query(query, head)
            if fixed and fixed != query:
                return search_gdelt_single(
                    fixed, max_results=max_results, start=start, end=end, timespan=timespan, timeout=timeout
                )
            return []
        data = r.json() or {}
        arts = data.get("articles", []) or []
        return [a.get("url") for a in arts if a.get("url")]
    except Exception as e:
        print(f"[!] GDELT search failed: {e}")
        return []


def search_gdelt_variants(
    sentence: str,
    *,
    exclude_domain: str | None = None,
    limit: int | None = None,
    start: str | datetime | None = None,
    end: str | datetime | None = None,
    timespan: str | None = None,
) -> list[str]:
    """Build a few query variants from the input sentence and union their results"""
    urls: list[str] = []
    seen: set[str] = set()

    limit = DEFAULTS["gdelt"]["limit"] if limit is None else limit
    timespan = DEFAULTS["gdelt"]["timespan"] if timespan is None else timespan

    for q in build_gdelt_queries(sentence, exclude_domain=exclude_domain):
        hits = search_gdelt_single(q, max_results=limit, start=start, end=end, timespan=timespan)
        for u in hits:
            if u and u not in seen:
                seen.add(u)
                urls.append(u)
            if len(urls) >= limit:
                return urls
    return urls