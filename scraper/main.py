import requests
import json
import os

# ------------------------
# SAS Scraper via JSON API
# ------------------------

def fetch_sas_shops():
    API_URL = "https://onlineshopping.loyaltykey.com/api/v1/shops"
    params = {
        "filter[channel]": "SAS",
        "filter[language]": "nb",
        "filter[country]": "NO",
        "filter[amount]": 5000,
        "filter[compressed]": "true"
    }

    try:
        resp = requests.get(API_URL, params=params, timeout=15)
        resp.raise_for_status()
    except Exception as e:
        print(f"Failed to fetch SAS shops: {e}")
        return []

    data = resp.json()
    shops = []
    for shop in data.get("shops", []):
        shops.append({
            "name": shop.get("name"),
            "bonus": shop.get("bonusPercentage") or shop.get("bonusAmount"),
            "type": "SAS"
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
