import requests
import json
import os

PATCHES_FILE = os.path.join(os.path.dirname(__file__), "patches.json")
OUTPUT_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "shops.json")

# ------------------------
# Helper: load patches
# ------------------------
def load_patches():
    if os.path.exists(PATCHES_FILE):
        with open(PATCHES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

# ------------------------
# Helper: save patches
# ------------------------
def save_patches(patches):
    with open(PATCHES_FILE, "w", encoding="utf-8") as f:
        json.dump(patches, f, ensure_ascii=False, indent=4)

# ------------------------
# Helper: validate domain
# ------------------------
def valid_domain(domain):
    url = f"https://{domain}"
    try:
        resp = requests.head(url, timeout=5)
        return resp.status_code < 400
    except:
        return False

# ------------------------
# Fetch SAS shops via API
# ------------------------
def fetch_sas_shops():
    API_URL = "https://onlineshopping.loyaltykey.com/api/v1/shops"
    params = {
        "filter[channel]": "SAS",
        "filter[language]": "nb",
        "filter[country]": "NO"
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*"
    }

    resp = requests.get(API_URL, params=params, headers=headers, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    return data.get("data", [])

# ------------------------
# Main
# ------------------------
def main():
    patches = load_patches()
    all_shops = []

    print("Fetching SAS shops via API...")
    sas_shops = fetch_sas_shops()
    print(f"Found {len(sas_shops)} shops from SAS API")

    for shop in sas_shops:
        slug = shop.get("slug")
        shop_entry = {
            "name": shop.get("name"),
            "type": "SAS",
            "bonus": None,
            "slug": slug,
            "domain": None,
            "image": shop.get("image_url"),
            "description": shop.get("description")
        }

        # Determine bonus
        if shop.get("currency") == "%":
            shop_entry["bonus"] = f"{shop.get('points')} %"
        elif shop.get("commission_type") == "fixed":
            shop_entry["bonus"] = f"{shop.get('points')} kr"
        elif shop.get("commission_type") == "variable":
            shop_entry["bonus"] = f"{shop.get('points')} %"

        # Domain resolution
        if slug in patches and patches[slug]:
            shop_entry["domain"] = patches[slug]
        else:
            # Heuristic: slug + .com
            domain_guess = f"{slug}.com"
            if valid_domain(domain_guess):
                shop_entry["domain"] = domain_guess
            else:
                shop_entry["domain"] = None
                # Add to patches if missing
                if slug not in patches:
                    patches[slug] = None

        all_shops.append(shop_entry)

    # Save shops.json
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(all_shops, f, ensure_ascii=False, indent=4)
    print(f"Saved {len(all_shops)} shops to {OUTPUT_FILE}")

    # Save updated patches.json
    save_patches(patches)
    print(f"Updated patches.json with unresolved domains")

# ------------------------
if __name__ == "__main__":
    main()
