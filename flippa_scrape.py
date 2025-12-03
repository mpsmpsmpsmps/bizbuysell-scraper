import os
import json
import requests
import gspread
from bs4 import BeautifulSoup
from google.oauth2.service_account import Credentials

SHEET_NAME = "BizBuySell — Listings"  # same spreadsheet
TAB_NAME = "Flippa"                   # the tab we just created


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
    Fetch Flippa listings by scraping search pages.
    This is a simple HTML scraper – not perfect, but good enough for a deal-finding dashboard.
    """
    base_url = "https://flippa.com/search"
    all_rows = []

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    for page in range(1, pages + 1):
        params = {
            "page": page,
            # You can add filters here later, e.g.:
            # "filters[property_type]": "online-businesses"
        }
        print(f"Fetching Flippa page {page}...")
        r = requests.get(base_url, params=params, headers=headers, timeout=20)
        r.raise_for_status()

        soup = BeautifulSoup(r.text, "html.parser")

        # Flippa uses cards for listings – classes can change over time,
        # but this selector should get us started.
        cards = soup.select("a[href^='/listing/']")
        print(f"Found {len(cards)} card anchors on page {page}.")

        for a in cards:
            href = a.get("href")
            url = "https://flippa.com" + href

            # We try to extract title & snippet from surrounding elements
            title = a.get_text(strip=True)

            # Sometimes the price is in a nearby span or div
            parent = a.find_parent("div")
            price_text = ""
            asset_type = ""
            short_desc = ""

            if parent:
                # naive attempts to find nearby text for price and description
                price_el = parent.find(string=lambda s: "$" in s) if parent else None
                price_text = price_el.strip() if price_el else ""

                # look for asset type or category in nearby spans/divs
                asset_type_el = parent.find("span")
                asset_type = asset_type_el.get_text(strip=True) if asset_type_el else ""

                # short description – next sibling text
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
    listings = fetch_flippa_listings(pages=2)  # start with 2 pages; adjust as needed
    write_to_sheet(listings)
    print("Flippa listings updated.")


if __name__ == "__main__":
    main()
