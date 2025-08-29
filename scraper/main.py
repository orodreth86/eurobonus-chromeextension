import requests
import json
import os
import re

# Absolute paths for consistency in GitHub Actions
PATCHES_FILE = os.path.abspath("scraper/patches.json")
OUTPUT_FILE = os.path.abspath("shops.json")

def load_patches():
    if os.path.exists(PATCHES_FILE):
        with open(PATCHES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_patches(patches):
    os.makedirs(os.path.dirname(PATCHES_FILE), exist_ok=True)  # ensure folder exists
    with open(PATCHES_FILE, "w", encoding="utf-8") as f:
        json.dump(patches, f, ensure_ascii=False, indent=4)
    print(f"Saved patches.json at {PATCHES_FILE} with {len(patches)} slugs")

def fetch_sas_shops():
    API_URL = "https://onlineshopping.loyaltykey.com/api/v1/shops"
    params = {
        "filter[channel]": "SAS",
        "filter[language]": "nb",
        "filter[country]": "NO",
        "filter[amount]": 5000  # fetch all shops
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*"
    }
    resp = requests.get(API_URL, params=params, headers=headers, timeout=15)
    resp.raise_for_status()
    return resp.json().get("data", [])

def domain_from_description(description):
    if not description:
        return None
    match = re.search(r"(https?://)?(www\.)?([a-z0-9\-]+)\.(no|se|com)", description, re.I)
    if match:
        return match.group(3) + '.' + match.group(4)
    return None

def heuristic_domain(slug):
    if slug.endswith("-no"):
        return slug[:-3] + ".no"
    elif slug.endswith("-se"):
        return slug[:-3] + ".se"
    else:
        return slug + ".com"

def main():
    patches = load_patches()
    all_shops = []

    print("Fetching SAS shops from API...")
    sas_shops = fetch_sas_shops()
    print(f"Found {len(sas_shops)} shops from SAS API")

    new_or_heuristic_count = 0
    missing_count = 0

    for shop in sas_shops:
        slug = shop.get("slug")
        description = shop.get("description")

        domain = None
        needs_review = False
        missing = False

        # Check existing patch
        if slug in patches and "domain" in patches[slug] and patches[slug]["domain"]:
            domain = patches[slug]["domain"]
            needs_review = patches[slug].get("needs_review", False)
            missing = patches[slug].get("missing", False)
        else:
            # Try description
            domain = domain_from_description(description)
            if domain:
                needs_review = True
            else:
                domain = heuristic_domain(slug)
                needs_review = True

        if not domain:
            domain = "unknown"
            missing = True
            missing_count += 1

        if needs_review:
            new_or_heuristic_count += 1

        # Update patches.json entry
        patches[slug] = {
            "domain": domain,
            "needs_review": needs_review,
            "missing": missing
        }

        # Prepare shop entry for shops.json
        shop_entry = {
            "name": shop.get("name"),
            "type": "SAS",
            "bonus": None,
            "slug": slug,
            "domain": domain if not missing else "",  # shops.json cannot have null
            "image": shop.get("image_url"),
            "description": description
        }

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
    print(f"Saved patches.json with {len(patches)} slugs, {new_or_heuristic_count} heuristic/new, {missing_count} missing")

if __name__ == "__main__":
    main()
