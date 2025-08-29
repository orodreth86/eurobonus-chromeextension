import requests
import json
import os

PATCHES_FILE = os.path.join(os.path.dirname(__file__), "patches.json")
OUTPUT_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "shops.json")

# ------------------------
# Load patches
# ------------------------
def load_patches():
    if os.path.exists(PATCHES_FILE):
        with open(PATCHES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

# ------------------------
# Save patches
# ------------------------
def save_patches(patches):
    with open(PATCHES_FILE, "w", encoding="utf-8") as f:
        json.dump(patches, f, ensure_ascii=False, indent=4)

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

        # Domain resolution using patches first
        if slug in patches and patches[slug]:
            shop_entry["domain"] = patches[slug]
        else:
            # Country-aware heuristic
            if slug.endswith("-no"):
                base_slug = slug[:-3]
                shop_entry["domain"] = f"{base_slug}.no"
            elif slug.endswith("-se"):
                base_slug = slug[:-3]
                shop_entry["domain"] = f"{base_slug}.se"
            else:
                shop_entry["domain"] = f"{slug}.com"

            # Add unresolved slug to patches for manual fix if needed
            if slug not in patches:
                patches[slug] = None if shop_entry["domain"] is None else shop_entry["domain"]

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
