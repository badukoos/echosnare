import os
import json
import subprocess
import whois
import time
import requests
from urllib.parse import urlparse

OUTPUT_FILE = "data/enrichment/domain_enrichment.json"
INPUT_FILE = "data/output/new_source_labels.json"

os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)

def extract_domains(freq_json):
    with open(freq_json, "r") as f:
        data = json.load(f)
    return list(data.keys())

def run_subfinder(domain):
    try:
        result = subprocess.run([
            "subfinder", "-d", domain, "-silent"
        ], capture_output=True, text=True)
        return result.stdout.strip().split("\n")
    except Exception as e:
        print(f"[!] subfinder failed for {domain}: {e}")
        return []

def fetch_whois(domain):
    try:
        w = whois.whois(domain)
        return {
            "registrar": w.registrar,
            "creation_date": str(w.creation_date),
            "emails": w.emails if isinstance(w.emails, list) else [w.emails],
            "org": w.org
        }
    except Exception as e:
        print(f"[!] WHOIS failed for {domain}: {e}")
        return {}

def fetch_crtsh(domain):
    try:
        url = f"https://crt.sh/?q=%25.{domain}&output=json"
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            certs = resp.json()
            results = []
            seen_serials = set()

            for cert in certs:
                serial = cert.get("serial_number")
                if not serial or serial in seen_serials:
                    continue
                seen_serials.add(serial)

                name_value = cert.get("name_value", "")
                domains = list(set(name_value.split("\n")))
                results.append({
                    "serial_number": serial,
                    "domains": domains,
                    "entry_timestamp": cert.get("entry_timestamp"),
                    "not_before": cert.get("not_before"),
                    "not_after": cert.get("not_after"),
                    "issuer_name": cert.get("issuer_name")
                })
            return results
    except Exception as e:
        print(f"[!] crt.sh lookup failed for {domain}: {e}")
    return []


def enrich_domain(domain):
    print(f"[*] Enriching: {domain}")
    subdomains = run_subfinder(domain)
    crtsh_certs = fetch_crtsh(domain)
    whois_info = fetch_whois(domain)

    return {
        "subfinder_subdomains": subdomains,
        "crtsh_certificates": crtsh_certs,
        "whois": whois_info
    }

def main():
    domains = extract_domains(INPUT_FILE)
    enriched = {}

    for domain in domains:
        enriched[domain] = enrich_domain(domain)
        time.sleep(2)  # Be considerate

    with open(OUTPUT_FILE, "w") as f:
        json.dump(enriched, f, indent=2)
    print(f"[✓] Enrichment complete. Saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
