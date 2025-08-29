import certifi
import requests
from bs4 import BeautifulSoup
import json
import re
from urllib.parse import urlparse, parse_qs, unquote


PATCH_FILE = "scraper/patches.json"
OUTPUT_FILE = "shops.json"


def load_patches():
    try:
        with open(PATCH_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def save_patches(patches):
    with open(PATCH_FILE, "w", encoding="utf-8") as f:
        json.dump(patches, f, indent=2, ensure_ascii=False)


def save_shops(shops):
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(shops, f, indent=2, ensure_ascii=False)


def extract_domain_from_url(url):
    """Try to find a real shop domain from an affiliate link"""
    if not url:
        return None

    # 1. Look for a query param that looks like a real URL
    parsed = urlparse(url)
    qs = parse_qs(parsed.query)
    for val_list in qs.values():
        for val in val_list:
            if val.startswith("http"):
                try:
                    hostname = urlparse(unquote(val)).hostname
                    if hostname:
                        return hostname.replace("www.", "")
                except Exception:
                    pass

    return None


def heuristic_domain(name):
    """Fallback: guess domain from shop name"""
    n = name.lower()
    # remove special chars
    n = re.sub(r"[^a-z0-9]", "", n)

    # If already looks like a domain (contains .no/.com/.se), return it
    if ".no" in name.lower() or ".com" in name.lower() or ".se" in name.lower():
        return name.lower().replace("www.", "")

    if not n:
        return None

    # Default guess: .no
    return f"{n}.no"


def scrape_trumf(patches):
    url = "https://trumfnetthandel.no/kategori"
    shops = []

    resp = requests.get(url, verify=certifi.where())
    soup = BeautifulSoup(resp.text, "html.parser")

    category_links = [a["href"] for a in soup.select("a.category-box") if "href" in a.attrs]

    for cat_url in category_links:
        r = requests.get(cat_url, verify=certifi.where())
        s = BeautifulSoup(r.text, "html.parser")
        category_name = s.select_one("h1").get_text(strip=True)

        for shop in s.select("div.shop-box"):
            name = shop.select_one("h3").get_text(strip=True)

            # Reward text (could be % or kr)
            reward_text = shop.get_text(" ", strip=True)
            rewards = []

            percents = re.findall(r"(\d+)\s*%", reward_text)
            for p in percents:
                rewards.append({
                    "type": "percentage",
                    "value": int(p),
                    "category": category_name
                })

            bonuses = re.findall(r"(\d+)\s*kr", reward_text)
            for b in bonuses:
                rewards.append({
                    "type": "fixed_bonus",
                    "value": int(b),
                    "category": category_name
                })

            aff_link = shop.select_one("a")["href"] if shop.select_one("a") else None
            domain = extract_domain_from_url(aff_link)

            # Patches
            if not domain and name in patches and patches[name]:
                domain = patches[name]

            # Heuristic
            if not domain:
                domain = heuristic_domain(name)

            shops.append({
                "source": "Trumf",
                "name": name,
                "domain": domain,
                "rewards": rewards
            })

    return shops


def scrape_sas(patches):
    base = "https://onlineshopping.flysas.com/nb-NO/alle-butikker/"
    shops = []
    page = 1

    while True:
        url = f"{base}{page}"
        r = requests.get(url, verify=certifi.where())
        s = BeautifulSoup(r.text, "html.parser")

        shop_boxes = s.select("div.merchant-listing")
        if not shop_boxes:
            break  # no more pages

        for shop in shop_boxes:
            name = shop.select_one(".merchant-name").get_text(strip=True)
            reward_text = shop.get_text(" ", strip=True)

            rewards = []
            m = re.search(r"(\d+)\s*poeng\s*/\s*100\s*kr", reward_text)
            if m:
                rewards.append({
                    "type": "per_100kr",
                    "value": int(m.group(1))
                })

            m = re.search(r"(\d+)\s*poeng", reward_text)
            if m and not rewards:
                rewards.append({
                    "type": "signup_bonus",
                    "value": int(m.group(1))
                })

            aff_link = shop.select_one("a")["href"] if shop.select_one("a") else None
            domain = extract_domain_from_url(aff_link)

            # Patches
            if not domain and name in patches and patches[name]:
                domain = patches[name]

            # Heuristic
            if not domain:
                domain = heuristic_domain(name)

            shops.append({
                "source": "SAS",
                "name": name,
                "domain": domain,
                "rewards": rewards
            })

        page += 1

    return shops


def main():
    patches = load_patches()
    all_shops = []

    print("Scraping Trumf...")
    all_shops.extend(scrape_trumf(patches))

    print("Scraping SAS...")
    all_shops.extend(scrape_sas(patches))

    # Collect unresolved domains into patches.json
    updated = False
    for shop in all_shops:
        if not shop["domain"]:
            if shop["name"] not in patches:
                patches[shop["name"]] = None
                updated = True

    if updated:
        print("Updating patches.json with unresolved shops...")
        save_patches(patches)

    save_shops(all_shops)
    print(f"Saved {len(all_shops)} shops to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
