import json
import os
from collections import defaultdict

INPUT_PATH = "data/analysis/reuse_map.json"
LABELS_PATH = "data/output/new_source_labels.json"
OUTPUT_PATH = "data/analysis/reuse_anomalies.json"

os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)

with open(INPUT_PATH, "r", encoding="utf-8") as f:
    reuse_map = json.load(f)

with open(LABELS_PATH, "r", encoding="utf-8") as f:
    domain_labels = json.load(f)

anomalies = []

for content_hash, group in reuse_map.items():
    sources = group.get("sources", [])
    label_groups = defaultdict(list)

    for item in sources:
        domain = item["domain"]
        label = domain_labels.get(domain, "unclassified")
        label_groups[label].append(domain)

    labels_used = list(label_groups.keys())

    if len(sources) >= 2:
        anomalies.append({
            "content_hash": content_hash,
            "reused_on": [{"domain": item["domain"], "label": domain_labels.get(item["domain"], "unclassified")} for item in sources],
            "issue": "High frequency reuse"
        })

    elif len(labels_used) >= 2:
        anomalies.append({
            "content_hash": content_hash,
            "reused_on": [{"domain": item["domain"], "label": domain_labels.get(item["domain"], "unclassified")} for item in sources],
            "issue": "Cross-ideological reuse"
        })

    elif all(domain_labels.get(item["domain"], "unclassified") == "unclassified" for item in sources) and len(sources) >= 3:
        anomalies.append({
            "content_hash": content_hash,
            "reused_on": [{"domain": item["domain"], "label": "unclassified"} for item in sources],
            "issue": "Unclassified cluster reuse"
        })

with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
    json.dump(anomalies, f, indent=2, ensure_ascii=False)

print(f"[✓] Found {len(anomalies)} suspicious reuse cases. Saved to {OUTPUT_PATH}")
