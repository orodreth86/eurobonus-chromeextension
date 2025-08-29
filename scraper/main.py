import requests
import certifi
from bs4 import BeautifulSoup
import json
import re
import os

PATCHES_FILE = os.path.join(os.path.dirname(__file__), "patches.json")
SHOPS_FILE = os.path.join(os.path.dirname(__file__), "..", "shops.json")


def safe_get(url, **kwargs):
    """Try HTTPS request with verification, fall back to verify=False if needed."""
    try:
        return requests.get(url, verify=certifi.where(), timeout=30, **kwargs)
    except requests.exceptions.SSLError:
        print(f"⚠️ SSL verification failed for {url}, retrying without verification...")
        return requests.get(url, verify=False, timeout=30, **kwargs)


def load_patches():
    if os.path.exists(PATCHES_FILE):
        with open(PATCHES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_patches(patches):
    with open(PATCHES_FILE, "w", encoding="utf-8") as f:
        json.dump(patches, f, indent=2, ensure_ascii=False)


def extract_domain(url):
    if not url:
        return None
    match = re.search(r"https?://(?:www\.)?([^/]+)", url)
    return match.group(1).lower() if match else None


def scrape_trumf(patches):
    base_url = "https://trumfnetthandel.no"
    url = f"{base_url}/kategori"
    resp = safe_get(url)
    soup = BeautifulSoup(resp.text, "html.parser")

    shops = []
    for cat_link in soup.select(".category-link"):
        cat_url = base_url + cat_link.get("href")
        cat_resp = safe_get(cat_url)
        cat_soup = BeautifulSoup(cat_resp.text, "html.parser")

        for shop in cat_soup.select(".shop-item"):
            name = shop.select_one(".shop-name").get_text(strip=True)
            bonus = shop.select_one(".shop-bonus").get_text(strip=True) if shop.select_one(".shop-bonus") else None
            link_tag = shop.select_one("a")
            shop_url = link_tag["href"] if link_tag else None

            domain = None
            if name in patches.get("trumf", {}):
                domain = patches["trumf"][name]
            else:
                domain = extract_domain(shop_url)

            shops.append({
                "program": "trumf",
                "name": name,
                "bonus": bonus,
                "domain": domain
            })

    return shops


def scrape_sas(patches):
    base_url = "https://onlineshopping.flysas.com"
    url = f"{base_url}/nb-NO/alle-butikker/1"
    resp = safe_get(url)
    soup = BeautifulSoup(resp.text, "html.parser")

    shops = []
    for shop in soup.select(".store-list-item"):
        name = shop.select_one(".store-name").get_text(strip=True)
        bonus = shop.select_one(".store-info").get_text(strip=True) if shop.select_one(".store-info") else None
        link_tag = shop.select_one("a")
        shop_url = base_url + link_tag["href"] if link_tag else None

        domain = None
        if name in patches.get("sas", {}):
            domain = patches["sas"][name]
        else:
            domain = extract_domain(shop_url)

        shops.append({
            "program": "sas",
            "name": name,
            "bonus": bonus,
            "domain": domain
        })

    return shops


def main():
    patches = load_patches()
    all_shops = []

    all_shops.extend(scrape_trumf(patches))
    all_shops.extend(scrape_sas(patches))

    # update patches.json with unresolved shops
    updated = False
    for shop in all_shops:
        if shop["domain"] is None:
            program = shop["program"]
            name = shop["name"]
            if program not in patches:
                patches[program] = {}
            if name not in patches[program]:
                patches[program][name] = None
                updated = True

    if updated:
        save_patches(patches)

    with open(SHOPS_FILE, "w", encoding="utf-8") as f:
        json.dump(all_shops, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    main()
