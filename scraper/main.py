import requests
import json
import os

# ------------------------
# SAS Scraper via API
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

    try:
        resp = requests.get(API_URL, params=params, headers=headers, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"Failed to fetch SAS shops: {e}")
        return []

    shops = []
    for shop in data.get("data", []):
        # Determine bonus format
        bonus = None
        if shop.get("currency") == "%":
            bonus = f"{shop.get('points')} %"
        elif shop.get("commission_type") == "fixed":
            bonus = f"{shop.get('points')} kr"
        elif shop.get("commission_type") == "variable":
            bonus = f"{shop.get('points')} %"

        shops.append({
            "name": shop.get("name"),
            "type": "SAS",
            "bonus": bonus,
            "slug": shop.get("slug"),
            "image": shop.get("image_url"),
            "description": shop.get("description")
        })

    return shops

# ------------------------
# Main
# ------------------------
def main():
    all_shops = []

    print("Fetching SAS shops via API...")
    sas_shops = fetch_sas_shops()
    print(f"Found {len(sas_shops)} SAS shops")
    all_shops.extend(sas_shops)

    # Save to shops.json in repo root
    output_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "shops.json")
    print(f"Saving {len(all_shops)} shops to {output_file}...")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(all_shops, f, ensure_ascii=False, indent=4)
    print("Done.")

# ------------------------
if __name__ == "__main__":
    main()
