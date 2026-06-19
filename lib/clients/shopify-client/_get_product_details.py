import json
import os
import sys
import urllib.request

from dotenv import load_dotenv

load_dotenv()
TOKEN = os.environ["SHOPIFY__TOKEN__ADMIN"]
STORE = os.environ["SHOPIFY__STORE_ID"]
VER = os.environ.get("SHOPIFY__API_VERSION", "2025-01")
URL = f"https://{STORE}.myshopify.com/admin/api/{VER}/graphql.json"

Q = """
query($id: ID!) {
  product(id: $id) {
    id title status tags handle totalInventory
    variants(first: 30) {
      nodes { id title inventoryQuantity inventoryPolicy availableForSale }
    }
    publications: resourcePublicationsV2(first: 10) {
      nodes { isPublished publication { name } }
    }
  }
}
"""


def fetch(pid: str) -> dict:
    gid = pid if pid.startswith("gid://") else f"gid://shopify/Product/{pid}"
    data = json.dumps({"query": Q, "variables": {"id": gid}}).encode()
    req = urllib.request.Request(
        URL, data=data,
        headers={"Content-Type": "application/json", "X-Shopify-Access-Token": TOKEN},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


for pid in sys.argv[1:]:
    res = fetch(pid)
    p = res.get("data", {}).get("product")
    print("=" * 80)
    if not p:
        print(pid, "NOT FOUND", res.get("errors"))
        continue
    print(f"{pid} -> {p['title']!r}")
    print(f"  status={p['status']} totalInventory={p['totalInventory']} handle={p['handle']}")
    print(f"  tags={p['tags']}")
    print(f"  published: " + ", ".join(
        f"{n['publication']['name']}={n['isPublished']}" for n in p["publications"]["nodes"]))
    print("  variants:")
    for v in p["variants"]["nodes"]:
        print(f"    {v['id'].split('/')[-1]:>15}  qty={v['inventoryQuantity']:>4}  "
              f"policy={v['inventoryPolicy']}  forSale={v['availableForSale']}  {v['title']!r}")
