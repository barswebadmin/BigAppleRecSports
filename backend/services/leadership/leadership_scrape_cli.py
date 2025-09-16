from __future__ import annotations

import argparse
import json
import os
from typing import Dict, List

from .leadership_contact_scraper import LeadershipContactScraper


def main() -> int:
    parser = argparse.ArgumentParser(description="Scrape BARS contact page for leadership assignments")
    parser.add_argument("--html", default="/workspace/data/bap_contact.html", help="Path to saved contact HTML")
    parser.add_argument("--json", default="/workspace/data/leadership_assignments.json", help="Output JSON path")
    args = parser.parse_args()

    if not os.path.exists(args.html):
        print(f"❌ HTML file not found: {args.html}")
        return 1

    html = open(args.html, "r", encoding="utf-8").read()
    scraper = LeadershipContactScraper(html)
    assignments = scraper.parse()

    # Group by sport-night-division -> {director: [], ops: []}
    grouped: Dict[str, Dict[str, List[str]]] = {}
    for a in assignments:
        key = a.group_key
        bucket = grouped.setdefault(key, {"director": [], "ops": []})
        if a.role == "Director":
            bucket["director"].append(a.person)
        elif a.role == "Operations Manager":
            bucket["ops"].append(a.person)

    os.makedirs(os.path.dirname(args.json), exist_ok=True)
    with open(args.json, "w", encoding="utf-8") as f:
        json.dump(grouped, f, indent=2, ensure_ascii=False)

    print(f"✅ Parsed {len(assignments)} assignments; {len(grouped)} groups written to {args.json}")
    # Print a small sample to stdout
    for k, v in list(grouped.items())[:8]:
        print(f"- {k}: directors={len(v['director'])}, ops={len(v['ops'])}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

