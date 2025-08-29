import requests
import json
import os
import re

PATCHES_FILE = os.path.join(os.path.dirname(__file__), "patches.json")
OUTPUT_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "shops.json")

# ------------------------
# Load patches.json
# ------------------------
def load_patches():
    if os.path.exists(PATCHES_FILE):
        with open(PATCHES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

# ------------------------
# Save patches.json
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
    return resp.json().get("data", [])

# ------------------------
# Extract domain from description
# ------------------------
def domain_from_description(description):
    if not description:
        return None
    match = re.search(r"(https?://)?(www\.)?([a-z0-9\-]+)\.(no|se|com)", description, re.I)
    if match:
        return match.group(3) + '.' + match.group(4)
    return None

# ------------------------
# Heuristic domain
# ------------------------
def heuristic_domain(slug):
    if slug.endswith("-no"):
        return slug[:-3] + ".no"
    elif slug.endswith("-se"):
        return slug[:-3] + ".se"
    else:
        return slug + ".com"

# ------------------------
# Main
# ------------------------
def main():
    patches = load_patches()  # Load existing patches or empty dict
    all_shops = []

    print("Fetching SAS shops from API...")
    sas_shops = fetch_sas_shops()
    print(f"Found {len(sas_shops)} shops")

    for shop in sas_shops:
        slug = shop.get("slug")
        description = shop.get("description")

        # Resolve domain
        if slug in patches and patches[slug]:
            domain = patches[slug]
        else:
            # Try description first
            domain = domain_from_description(description)
            if not domain:
                # Heuristic
                domain = heuristic_domain(slug)

        # Always update patches.json
        patches[slug] = domain

        # Prepare shop entry for shops.json
        shop_entry = {
            "name": shop.get("name"),
            "type": "SAS",
            "bonus": None,
            "slug": slug,
            "domain": domain,  # always populated
            "image": shop.get("image_url"),
            "description": description
        }

        # Determine bonus
        if shop.get("currency") == "%":
            shop_entry["bonus"] = f"{shop.get('points')} %"
        elif shop.get("commission_type") == "fixed":
            shop_entry["bonus"] = f"{shop.get('points')} kr"
        elif shop.get("commission_type") == "variable":
            shop_entry["bonus"] = f"{shop.get('points')} %"

        all_shops.append(shop_entry)

    # Save shops.json
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(all_shops, f, ensure_ascii=False, indent=4)
    print(f"Saved {len(all_shops)} shops to {OUTPUT_FILE}")

    # Save patches.json
    save_patches(patches)
    print(f"Saved patches.json with {len(patches)} slugs and their domains")

if __name__ == "__main__":
    main()
