import os
import json
import requests
import gspread
from bs4 import BeautifulSoup
from google.oauth2.service_account import Credentials

SHEET_NAME = "BizBuySell — Listings"  # same spreadsheet
TAB_NAME = "Flippa"                   # the tab we created


def authorize_gsheet():
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
    """
    api_key = os.environ.get("SCRAPER_API_KEY")
    if not api_key:
        raise RuntimeError("SCRAPER_API_KEY environment variable is missing")

    base_target = "https://flippa.com/search"
    scraper_url = "https://api.scraperapi.com/"  # ScraperAPI endpoint

    all_rows = []

    for page in range(1, pages + 1):
        target_url = f"{base_target}?page={page}"
        params = {
            "api_key": api_key,
            "url": target_url,
            # render=true uses a headless browser to execute JS – needed for Flippa search
            "render": "true",
        }
        print(f"Fetching Flippa page {page} via ScraperAPI...")
        r = requests.get(scraper_url, params=params, timeout=60)
        print("Status code:", r.status_code)
        r.raise_for_status()

        soup = BeautifulSoup(r.text, "html.parser")

        # Flippa uses listing links like /listing/xyz
        cards = soup.select("a[href^='/listing/']")
        print(f"Found {len(cards)} listing anchors on page {page}.")

        for a in cards:
            href = a.get("href")
            if not href:
                continue

            url = "https://flippa.com" + href
            title = a.get_text(strip=True)

            # Try to grab nearby text for price / type
            parent = a.find_parent("div")
            price_text = ""
            asset_type = ""
            short_desc = ""

            if parent:
                # Very naive heuristics – can refine once we see real HTML
                # Look for a sibling span/div with a dollar sign
                price_el = None
                for el in parent.find_all(string=True):
                    if "$" in el:
                        price_el = el
                        break
                price_text = price_el.strip() if price_el else ""

                # Asset type often appears in a span
                asset_type_el = parent.find("span")
                asset_type = asset_type_el.get_text(strip=True) if asset_type_el else ""

                # Short description – try the next sibling text
                if parent.next_sibling:
                    short_desc = str(parent.next_sibling).strip()

            all_rows.append([title, url, price_text, asset_type, short_desc])

    return all_rows


def write_to_sheet(rows):
    client = authorize_gsheet()
    sheet = client.open(SHEET_NAME).worksheet(TAB_NAME)

    # Clear existing data
    sheet.clear()

    # Prepend header row
    header = ["Title", "URL", "Price", "Asset Type", "Short Description"]
    rows_with_header = [header] + rows

    print(f"Writing {len(rows)} listings to Flippa tab...")
    sheet.update(rows_with_header)


def main():
    listings = fetch_flippa_listings(pages=1)  # start with 1 page to keep usage low
    write_to_sheet(listings)
    print("Flippa listings updated.")


if __name__ == "__main__":
    main()
