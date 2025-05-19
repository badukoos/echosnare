
# EchoSnare

**EchoSnare** is an OSINT tool built to track the amplification of propaganda or misinformation by fringe and coordinated websites that launder narratives across low-credibility sources. The project focuses on:

- Tracing the reuse of content from original articles
- Identifying narrative amplification through search engines (currently supporting DuckDuckGo and Google)
- Extracting and comparing article content
- Labeling and enriching source domain data
- Analyzing content reuse frequency and associated metadata

---

## ⚙️ Setup

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install requirements
pip install -r requirements.txt
```

---

## 🔀 Workflow

### 1. Run the Spider on a Seed Article

Search and match similar articles using search engines.

```bash
PYTHONPATH=src python src/crawler/echo_spider.py \
      "https://www.rt.com/india/617713-west-pitting-india-against-china/" \
      --engine google \
      # Ensures that only articles with 80% or more similarity to the seed article are selected
      --threshold=0.8 \
      # Adds a 5 second pause between requests to avoid overwhelming the search engine (esp for duckduckgo)
      --delay=5
```

**Output:**
`data/crawled/matches_google.json` - articles similar to the seed.

---

### 2. Label Matched Articles Using Known Source Labels

Assign credibility labels like `credible`, `state-sponsored`, `conspiratorial` or `unclassified`.

```bash
python scripts/enrich_with_labels.py \
       data/crawled/matches_google.json \
       data/config/source_labels.json \
       data/output/matches_google_labeled.json
```

---

### 3. Generate Template for New Domains

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

### 4. Compute Domain Reuse Frequency

Check which domains are used most frequently across searches.

```bash
python scripts/domain_frequency_report.py
```

---

### 5. Generate Matched Snippets for Manual Review

Store the first 1000 characters of each matched article for review.

```bash
python scripts/trace_content_reuse.py
```

---

### 6. Detect Suspicious Reuse Patterns

Check how often does the reuse pattern appear across multiple sub-domains

```bash
python scripts/detect_reuse_anomalies.py
```

---
### 7. Enrich Domains with WHOIS and Subdomain Info

Fetch **basic** metadata for each domain using `whois`, `crt.sh`, and `subfinder`.

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
         "feeds.fringe-news.co"
         "www.fringe-news.co"
       ],
       "crtsh_subdomains": [
         "*.fringe-news.co"
       ],
       "whois": {
         "registrar": "GoDaddy.com, LLC",
         "creation_date": "[...]",
         "emails": [
           "abuse@godaddy.com"
         ],
         "org": "Domains By Proxy, LLC"
       }
   }
}
```

> Note: Install `subfinder` for this to work properly.

---

## 📝 To-do

- Integrate GDELT search.
- Better domain enrichment using WHOIS history. Cluster domains by WHOIS fingerprint (same registrar/org/email).
- Reverse IP & passive DNS correlation.

---

## 🧾 License

MIT License, see `LICENSE` file.
