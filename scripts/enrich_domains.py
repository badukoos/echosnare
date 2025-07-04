#!/usr/bin/env python3
"""Domain enrichment tool that gathers WHOIS, subdomains, and certificate data."""

import os
import json
import time
import argparse
import subprocess
import requests
import whois
from cryptography import x509
from cryptography.hazmat.backends import default_backend
from typing import Dict, List, Optional, Any


class DomainEnricher:
    def __init__(self, cache_dir: str = ".cache/certs", rate_limit_delay: int = 12, max_certs: int = 1):
        self.cache_dir = cache_dir
        self.rate_limit_delay = rate_limit_delay
        self.max_certs = max_certs
        self.last_request_time = 0
        os.makedirs(self.cache_dir, exist_ok=True)

    def extract_domains(self, input_file: str) -> List[str]:
        """Extract domains from input JSON file."""
        with open(input_file, "r") as f:
            data = json.load(f)
        return list(data.keys())

    def run_subfinder(self, domain: str) -> List[str]:
        """Run subfinder to discover subdomains."""
        try:
            result = subprocess.run(
                ["subfinder", "-d", domain, "-silent"],
                capture_output=True,
                text=True
            )
            return result.stdout.strip().split("\n")
        except Exception as e:
            print(f"[!] subfinder failed for {domain}: {e}")
            return []

    def fetch_whois(self, domain: str) -> Dict[str, Any]:
        """Fetch WHOIS information for a domain."""
        try:
            w = whois.whois(domain)
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

    def _load_from_cache(self, cert_id: str) -> Optional[bytes]:
        """Load certificate from cache if exists."""
        path = os.path.join(self.cache_dir, f"{cert_id}.der")
        if os.path.exists(path):
            with open(path, "rb") as f:
                return f.read()
        return None

    def _save_to_cache(self, cert_id: str, content: bytes) -> None:
        """Save certificate to cache."""
        path = os.path.join(self.cache_dir, f"{cert_id}.der")
        with open(path, "wb") as f:
            f.write(content)

    def _download_cert(self, cert_id: str) -> Optional[bytes]:
        """Download certificate from crt.sh with rate limiting."""
        cached = self._load_from_cache(cert_id)
        if cached:
            return cached

        now = time.time()
        elapsed = now - self.last_request_time
        if elapsed < self.rate_limit_delay:
            time.sleep(self.rate_limit_delay - elapsed)

        try:
            url = f"https://crt.sh/?d={cert_id}"
            resp = requests.get(url, timeout=15)
            self.last_request_time = time.time()

            if resp.status_code == 200:
                if b"<html" in resp.content[:100].lower():
                    print(f"[!] Skipped HTML page for cert {cert_id}")
                    return None
                self._save_to_cache(cert_id, resp.content)
                return resp.content
            print(f"[!] Error {resp.status_code} for cert {cert_id}")
        except Exception as e:
            print(f"[!] Request failed for cert {cert_id}: {e}")
        return None

    def _extract_san(self, cert: x509.Certificate) -> List[str]:
        """Extract Subject Alternative Names from certificate."""
        try:
            san = cert.extensions.get_extension_for_class(x509.SubjectAlternativeName)
            return san.value.get_values_for_type(x509.DNSName)
        except x509.ExtensionNotFound:
            return []

    def _parse_cert(self, content: bytes) -> Optional[Dict[str, Any]]:
        """Parse certificate content."""
        try:
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
                "san_domains": self._extract_san(cert)
            }
        except Exception as e:
            print(f"[!] Failed to parse cert: {e}")
            return None

    def fetch_crtsh(self, domain: str) -> List[Dict[str, Any]]:
        """Fetch certificate information from crt.sh."""
        try:
            url = f"https://crt.sh/?q=%25.{domain}&output=json"
            resp = requests.get(url, timeout=15)
            if resp.status_code != 200:
                return []

            certs = resp.json()
            seen_serials = set()
            results = []

            for cert in certs:
                if len(results) >= self.max_certs:
                    break

                cert_id = cert.get("id")
                if not cert_id:
                    continue

                content = self._download_cert(cert_id)
                if not content:
                    continue

                cert_info = self._parse_cert(content)
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

    def enrich_domain(self, domain: str) -> Dict[str, Any]:
        """Enrich domain with subdomains, certificates, and WHOIS data."""
        print(f"[*] Enriching: {domain}")
        return {
            "subfinder_subdomains": self.run_subfinder(domain),
            "crtsh_certificates": self.fetch_crtsh(domain),
            "whois": self.fetch_whois(domain)
        }

    def generate_reverse_san_index(self, enriched_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate reverse index of SAN domains."""
        reverse_index = {}
        for domain, data in enriched_data.items():
            for cert in data.get("crtsh_certificates", []):
                serial = cert["serial_number"]
                for san_domain in cert["san_domains"]:
                    if san_domain not in reverse_index:
                        reverse_index[san_domain] = []
                    reverse_index[san_domain].append({
                        "shared_with": domain,
                        "serial_number": serial,
                        "issuer": cert["issuer"],
                        "not_before": cert["not_before"],
                        "not_after": cert["not_after"]
                    })
        return reverse_index


def main(input_path: str, output_dir: str, cache_dir: str, rate_limit: int, max_certs: int) -> None:
    """Main execution function."""
    os.makedirs(output_dir, exist_ok=True)
    enricher = DomainEnricher(cache_dir, rate_limit, max_certs)

    print(f"[*] Processing domains from {input_path}")
    domains = enricher.extract_domains(input_path)
    enriched = {}

    for domain in domains:
        enriched[domain] = enricher.enrich_domain(domain)
        time.sleep(2)

    output_file = os.path.join(output_dir, "domain_enrichment.json")
    with open(output_file, "w") as f:
        json.dump(enriched, f, indent=2)
    print(f"[✓] Enrichment complete. Saved to {output_file}")

    reverse_index = enricher.generate_reverse_san_index(enriched)
    reverse_index_file = os.path.join(output_dir, "reverse_san_index.json")
    with open(reverse_index_file, "w") as f:
        json.dump(reverse_index, f, indent=2)
    print(f"[✓] Reverse SAN index saved to {reverse_index_file}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Domain enrichment tool")
    parser.add_argument(
        "--input-path",
        default="data/output/new_source_labels.json",
        help="Input JSON file containing domains (default: data/output/new_source_labels.json)"
    )
    parser.add_argument(
        "--output-dir",
        default="data/enrichment",
        help="Output directory for results (default: data/enrichment)"
    )
    parser.add_argument(
        "--cache-dir",
        default=".cache/certs",
        help="Certificate cache directory (default: .cache/certs)"
    )
    parser.add_argument(
        "--rate-limit",
        type=int,
        default=12,
        help="Rate limit delay in seconds (default: 12)"
    )
    parser.add_argument(
        "--max-certs",
        type=int,
        default=1,
        help="Max certificates to fetch per domain (default: 1)"
    )

    args = parser.parse_args()
    main(
        args.input_path,
        args.output_dir,
        args.cache_dir,
        args.rate_limit,
        args.max_certs
    )