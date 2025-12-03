import os
import json
import requests
import gspread
from bs4 import BeautifulSoup
from google.oauth2.service_account import Credentials

# === CONFIG ===
SHEET_NAME = "BizBuySell — Listings"
SHEET_ID = "1_EvQAKLgYG4JyY19TbgsDAQGbeJeTwGlbB8znQnlwfU"
TAB_NAME = "Flippa"


def authorize_gsheet():
    """Authorize Google Sheets using the service account JSON in the env."""
    if "GOOGLE_SERVICE_ACCOUNT_JSON" not in os.environ:
        raise RuntimeError("GOOGLE_SERVICE_ACCOUNT_JSON environment variable is missing")

    service_account_info = json.loads(os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"])

    scopes = ["https://www.googleapis.com/auth/spreadsheets"]

    credentials = Credentials.from_service_account_info(
        service_account_info, scopes=scopes
    )
    client = gspread.authorize(credentials)
    return client


def fetch_flippa_listings(pages=1):
    """
    Fetch Flippa listings by scraping search pages via ScraperAPI.
    If ScraperAPI returns non-200, we log and skip instead of crashing.
    """
    api_key = os.environ.get("SCRAPER_API_KEY")
    if not api_key:
        raise RuntimeError("SCRAPER_API_KEY environment variable is missing")

    base_target = "https://flippa.com/search"
    scraper_url = "https://api.scraperapi.com/"

    all_rows = []

    for page in range(1, pages + 1):
        target_url = f"{base_target}?page={page}"
        params = {
            "api_key": api_key,
            "url": target_url,
            # IMPORTANT: drop render=true for now (can cause 500s on some plans)
            # "render": "true",
        }
        print(f"Fetching Flippa page {page} via ScraperAPI...")
        try:
            r = requests.get(scraper_url, params=params, timeout=60)
            print("Status code:", r.status_code)
        except Exception as e:
            print(f"Request error on page {page}: {e}")
            continue

        if r.status_code != 200:
            print(f"Non-200 from ScraperAPI on page {page}: {r.status_code}")
            # Skip this page instead of crashing
            continue

        soup = BeautifulSoup(r.text, "html.parser")

        # Very simple selector to start; may find 0 and that's okay for now
        cards = soup.select("a[href^='/listing/']")
        print(f"Found {len(cards)} listing anchors on page {page}.")

        for a in cards:
            href = a.get("href")
            if not href:
                continue

            url = "https://flippa.com" + href
            title = a.get_text(strip=True)

            parent = a.find_parent("div")
            price_text = ""
            asset_type = ""
            short_desc = ""

            if parent:
                price_el = None
                for el in parent.find_all(string=True):
                    if "$" in el:
                        price_el = el
                        break
                price_text = price_el.strip() if price_el else ""

                asset_type_el = parent.find("span")
                asset_type = asset_type_el.get_text(strip=True) if asset_type_el else ""

                if parent.next_sibling:
                    short_desc = str(parent.next_sibling).strip()

            all_rows.append([title, url, price_text, asset_type, short_desc])

    return all_rows


def write_to_sheet(rows):
    client = authorize_gsheet()
    sheet = client.open_by_key(SHEET_ID).worksheet(TAB_NAME)

    sheet.clear()

    header = ["Title", "URL", "Price", "Asset Type", "Short Description"]
    rows_with_header = [header] + rows

    print(f"Writing {len(rows)} listings to Flippa tab...")
    sheet.update(rows_with_header)


def main():
    listings = fetch_flippa_listings(pages=1)  # keep usage low
    print(f"Total listings scraped: {len(listings)}")
    write_to_sheet(listings)
    print("Flippa listings updated.")


if __name__ == "__main__":
    main()
