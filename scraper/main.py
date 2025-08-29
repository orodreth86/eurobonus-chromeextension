import requests
import json
import os
import re

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
# Resolve domain
# ------------------------
def resolve_domain(slug, description, patches):
    # 1. Use patches.json if available
    if slug in patches and patches[slug]:
        return patches[slug]

    # 2. Check description for domain
    domain = domain_from_description(description)
    if domain:
        return domain

    # 3. Country-aware heuristic
    if slug.endswith("-no"):
        return slug[:-3] + ".no"
    elif slug.endswith("-se"):
        return slug[:-3] + ".se"

    # 4. Default .com heuristic
    return slug + ".com"

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

        # Resolve domain
        resolved_domain = resolve_domain(slug, description, patches)
        shop_entry["domain"] = resolved_domain

        # Add unresolved domain to patches if not already there
        if slug not in patches or patches[slug] != resolved_domain:
            patches[slug] = resolved_domain

        all_shops.append(shop_entry)

    # Save shops.json
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(all_shops, f, ensure_ascii=False, indent=4)
    print(f"Saved {len(all_shops)} shops to {OUTPUT_FILE}")

    # Save updated patches.json
    save_patches(patches)
    print(f"Updated patches.json with all domains")

# ------------------------
if __name__ == "__main__":
    main()
