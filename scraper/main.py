import requests
import json
import os
import re

PATCHES_FILE = os.path.join(os.path.dirname(__file__), "patches.json")
OUTPUT_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "shops.json")

def load_patches():
    if os.path.exists(PATCHES_FILE):
        with open(PATCHES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_patches(patches):
    with open(PATCHES_FILE, "w", encoding="utf-8") as f:
        json.dump(patches, f, ensure_ascii=False, indent=4)

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

    print("Fetching SAS shops via API...")
    sas_shops = fetch_sas_shops()
    print(f"Found {len(sas_shops)} shops from SAS API")

    for shop in sas_shops:
        slug = shop.get("slug")
        description = shop.get("description")
        shop_entry = {
            "name": shop.get("name"),
            "type": "SAS",
            "bonus": None,
            "slug": slug,
            "domain": None,
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

        # Domain resolution
        if slug in patches and patches[slug]:
            resolved_domain = patches[slug]
        else:
            # Try description first
            resolved_domain = domain_from_description(description)
            if not resolved_domain:
                resolved_domain = heuristic_domain(slug)

        shop_entry["domain"] = resolved_domain

        # Always update patches.json with the resolved domain
        patches[slug] = resolved_domain

        all_shops.append(shop_entry)

    # Save shops.json
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(all_shops, f, ensure_ascii=False, indent=4)
    print(f"Saved {len(all_shops)} shops to {OUTPUT_FILE}")

    # Save patches.json (complete list of all slugs and their domains)
    save_patches(patches)
    print(f"Saved complete patches.json with all slugs and their domains")

if __name__ == "__main__":
    main()
