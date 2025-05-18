import requests
from bs4 import BeautifulSoup

def search_duckduckgo(query, max_results=10):
    results = []
    try:
        res = requests.post("https://html.duckduckgo.com/html/", data={"q": query}, headers={"User-Agent": "Mozilla/5.0"})
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

def search_google_cse(query, api_key, cse_id, num=10):
    """Google Custom Search API (requires setup)."""
    try:
        from googleapiclient.discovery import build
        service = build("customsearch", "v1", developerKey=api_key)
        res = service.cse().list(q=query, cx=cse_id, num=num).execute()
        return [item['link'] for item in res.get('items', [])]
    except Exception as e:
        print(f"[!] Google CSE failed: {e}")
        return []
