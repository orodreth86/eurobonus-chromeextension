import requests
from bs4 import BeautifulSoup
import json
import re

# ------------------------
# Helper functions
# ------------------------

def safe_get(url, **kwargs):
    """Perform a GET request safely, returns None if failed."""
    try:
        resp = requests.get(url, timeout=15, **kwargs)
        resp.raise_for_status()
        return resp
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None

# ------------------------
# Trumf Scraper
# ------------------------

def fetch_trumf_shops():
    url = "https://trumfnetthandel.no/kategori"
    resp = safe_get(url)
    if not resp:
        return []

    soup = BeautifulSoup(resp.text, "html.parser")

    # Find script containing JSON data
    script_tag = soup.find("script", string=re.compile("window.__DATA__"))
    if not script_tag:
        print("Trumf: Could not find script with JSON data.")
        return []

    match = re.search(r"window\.__DATA__ = ({.*?});", script_tag.string, re.DOTALL)
    if not match:
        print("Trumf: JSON data not found inside script.")
        return []

    data = json.loads(match.group(1))

    shops = []
    for category in data.get("categories", []):
        for shop in category.get("shops", []):
            shop_name = shop.get("name")
            bonus = shop.get("bonus_percentage") or shop.get("bonus_kr")  # support % or kr
            shops.append({
                "name": shop_name,
                "type": "Trumf",
                "bonus": bonus
            })

    return shops

# ------------------------
# SAS Scraper
# ------------------------

def fetch_sas_shops():
    api_url = "https://onlineshopping.flysas.com/api/stores"
    page = 1
    shops = []

    while True:
        resp = safe_get(api_url, params={"page": page})
        if not resp:
            break
        data = resp.json()
        stores = data.get("stores", [])
        if not stores:
            break

        for store in stores:
            shops.append({
                "name": store.get("name"),
                "type": "SAS",
                "bonus": store.get("bonus_percentage") or store.get("bonus_kr")
            })

        # Check if there are more pages
        if not data.get("hasNextPage"):
            break
        page += 1

    return shops

# ------------------------
# Main
# ------------------------

def main():
    all_shops = []

    print("Fetching Trumf shops...")
    trumf = fetch_trumf_shops()
    print(f"Found {len(trumf)} Trumf shops")
    all_shops.extend(trumf)

    print("Fetching SAS shops...")
    sas = fetch_sas_shops()
    print(f"Found {len(sas)} SAS shops")
    all_shops.extend(sas)

    print(f"Saving {len(all_shops)} shops to shops.json...")
    with open("shops.json", "w", encoding="utf-8") as f:
        json.dump(all_shops, f, ensure_ascii=False, indent=4)

    print("Done.")

# ------------------------
if __name__ == "__main__":
    main()
