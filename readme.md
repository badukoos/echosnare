
# EchoSnare

**EchoSnare** is an OSINT tool built to track the amplification of propaganda or misinformation by fringe and coordinated websites that launder narratives across low-credibility sources. The project focuses on:

- Tracing the reuse of content from original articles
- Identifying narrative amplification through search engines (currently supporting DuckDuckGo and Google)
- Extracting and comparing article content
- Labeling and enriching source domain data
- Analyzing content reuse frequency and associated metadata

---

## Setup

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install requirements
pip install -r requirements.txt
```

---

## Workflow

### Run the Spider on a Seed Article

Search and match similar articles using search engines.

```bash
PYTHONPATH=src python src/crawler/echo_spider.py \
      "https://www.rt.com/india/617713-west-pitting-india-against-china/" \
      --engine google \
      --threshold=0.8 \
      --delay=10
```

>**Output:** stored at `data/crawled/matches_google.json`<br>
>**Requires:** a Google API key and CSE ID

---

### Label Matched Articles Using Known Source Labels

Assign credibility labels like `credible`, `state-sponsored`, `conspiratorial` or `unclassified`.

```bash
python scripts/enrich_with_labels.py \
       data/crawled/matches_google.json \
       data/config/source_labels.json \
       data/output/matches_google_labeled.json
```

---

### Generate Template for New Domains

Extract new domains that are not in `source_labels.json` for manual labeling.

```bash
python scripts/generate_source_labels.py \
       data/crawled/matches_google.json \
       data/config/source_labels.json \
       data/output/new_source_labels.json
```

**Output:** New entries like:
```json
{
  "fringe-news.co": "unclassified",
  "altmedia.today": "unclassified"
}
```

---

### Compute Domain Reuse Frequency

Check which domains are used most frequently across searches.

```bash
python scripts/domain_frequency_report.py
```

---

### Detect Suspicious Reuse Patterns

Check how often does the reuse pattern appear across multiple sub-domains

```bash
python scripts/detect_reuse_anomalies.py
```

---
### Enrich Domains with WHOIS and Subdomain Info

Fetch **basic** metadata for each domain using

 - Subfinder (for discovering subdomains)
 - WHOIS (registrar, creation date, contact info, org). Only current info, WHOIS history might be included in the future.
 - crt.sh (from certificate transparency logs - issuer, SANs, serial numbers, also generates a reverse SAN index).

```bash
python scripts/enrich_domains.py
```

**Output:**
Enriched metadata file example:
```json
{
  "fringe-news.co": {
    "subfinder_subdomains": [
      "cdn.fringe-news.co",
      "feeds.fringe-news.co",
      "www.fringe-news.co"
    ],
    "crtsh_certificates": [
      {
        "serial_number": "04a5d7...",
        "not_before": "2024-02-01T00:00:00",
        "not_after": "2025-02-01T23:59:59",
        "issuer": "CN=Let's Encrypt Authority X3,O=Let's Encrypt,C=US",
        "subject_common_name": "CN=fringe-news.co",
        "san_domains": [
          "fringe-news.co",
          "www.fringe-news.co"
        ]
      }
    ],
    "whois": {
      "registrar": "GoDaddy.com, LLC",
      "creation_date": "2000-07-04 21:01:21",
      "emails": [
        "abuse@godaddy.com"
      ],
      "org": "Domains By Proxy, LLC"
    }
  }
}

```
>  - Install [`subfinder`](https://github.com/projectdiscovery/subfinder) for this to work properly.<br>
>  - Certificate downloads from [`crt.sh`](https://crt.sh) are rate-limited to [5 per minute at the moment](https://groups.google.com/g/crtsh/c/QXQFoy331pE).<br>
>  - Only 1 unique certificate per domain are processed (tunable via `MAX_CERTS`).


---

## To-do

- Integrate GDELT search.
- Better domain enrichment using WHOIS history. Cluster domains by WHOIS fingerprint (same registrar/org/email).
- Reverse IP & passive DNS correlation.

---

## License

MIT License, see `LICENSE` file.
