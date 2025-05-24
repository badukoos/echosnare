import os
import json
import subprocess
import whois
import time
import requests
from urllib.parse import urlparse
from cryptography import x509
from cryptography.hazmat.backends import default_backend

OUTPUT_FILE = "data/enrichment/domain_enrichment.json"
INPUT_FILE = "data/output/new_source_labels.json"
CACHE_DIR = ".cache/certs"
MAX_CERTS = 1  # Limit number of certs per domain
RATE_LIMIT_DELAY = 12  # 5 requests/min = 12 sec between requests

os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
os.makedirs(CACHE_DIR, exist_ok=True)

last_request_time = 0  # For rate limiting

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
        # Try to fallback to alternative fields if org is None
        org = w.org or w.get("name") or w.get("registrant_name")
        emails = w.emails if isinstance(w.emails, list) else [w.emails] if w.emails else []

        return {
            "registrar": w.registrar,
            "creation_date": str(w.creation_date),
            "emails": emails,
            "org": org
        }
    except Exception as e:
        print(f"[!] WHOIS failed for {domain}: {e}")
        return {}


def load_from_cache(cert_id):
    path = os.path.join(CACHE_DIR, f"{cert_id}.der")
    if os.path.exists(path):
        with open(path, "rb") as f:
            return f.read()
    return None

def save_to_cache(cert_id, content):
    path = os.path.join(CACHE_DIR, f"{cert_id}.der")
    with open(path, "wb") as f:
        f.write(content)

def download_cert(cert_id):
    global last_request_time

    cached = load_from_cache(cert_id)
    if cached:
        return cached

    now = time.time()
    elapsed = now - last_request_time
    if elapsed < RATE_LIMIT_DELAY:
        time.sleep(RATE_LIMIT_DELAY - elapsed)

    try:
        url = f"https://crt.sh/?d={cert_id}"
        resp = requests.get(url, timeout=15)
        last_request_time = time.time()

        if resp.status_code == 200:
            if b"<html" in resp.content[:100].lower():
                print(f"[!] Skipped HTML page for cert {cert_id}")
                return None
            save_to_cache(cert_id, resp.content)
            return resp.content
        else:
            print(f"[!] Error {resp.status_code} for cert {cert_id}")
            return None
    except Exception as e:
        print(f"[!] Request failed for cert {cert_id}: {e}")
        return None

def extract_san(cert):
    try:
        san = cert.extensions.get_extension_for_class(x509.SubjectAlternativeName)
        return san.value.get_values_for_type(x509.DNSName)
    except x509.ExtensionNotFound:
        return []

def download_and_parse_cert(cert_id):
    try:
        content = download_cert(cert_id)
        if not content:
            return None

        if b"-----BEGIN CERTIFICATE-----" in content:
            cert = x509.load_pem_x509_certificate(content, default_backend())
        else:
            cert = x509.load_der_x509_certificate(content, default_backend())

        return {
            "serial_number": format(cert.serial_number, "x"),
            "not_before": cert.not_valid_before_utc.isoformat(),
            "not_after": cert.not_valid_after_utc.isoformat(),
            "issuer": cert.issuer.rfc4514_string(),
            "subject_common_name": cert.subject.rfc4514_string(),
            "san_domains": extract_san(cert)
        }

    except Exception as e:
        print(f"[!] Failed to parse cert {cert_id}: {e}")
        return None

def fetch_crtsh(domain):
    try:
        url = f"https://crt.sh/?q=%25.{domain}&output=json"
        resp = requests.get(url, timeout=15)
        if resp.status_code != 200:
            return []

        certs = resp.json()
        seen_serials = set()
        results = []

        for cert in certs:
            if len(results) >= MAX_CERTS:
                break

            cert_id = cert.get("id")
            if not cert_id:
                continue

            cert_info = download_and_parse_cert(cert_id)
            if cert_info:
                fingerprint = (cert_info["issuer"], cert_info["serial_number"])
                if fingerprint in seen_serials:
                    continue
                seen_serials.add(fingerprint)

                if any(domain in d or f"*.{domain}" in d for d in cert_info["san_domains"]):
                    results.append(cert_info)

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
        time.sleep(2)

    with open(OUTPUT_FILE, "w") as f:
        json.dump(enriched, f, indent=2)
    print(f"[✓] Enrichment complete. Saved to {OUTPUT_FILE}")

    reverse_san_index = {}
    for domain, data in enriched.items():
        for cert in data.get("crtsh_certificates", []):
            serial = cert["serial_number"]
            for san_domain in cert["san_domains"]:
                if san_domain not in reverse_san_index:
                    reverse_san_index[san_domain] = []
                reverse_san_index[san_domain].append({
                    "shared_with": domain,
                    "serial_number": serial,
                    "issuer": cert["issuer"],
                    "not_before": cert["not_before"],
                    "not_after": cert["not_after"]
                })

    with open("data/enrichment/reverse_san_index.json", "w") as f:
        json.dump(reverse_san_index, f, indent=2)
    print(f"[✓] Reverse SAN index saved to data/enrichment/reverse_san_index.json")

if __name__ == "__main__":
    main()
