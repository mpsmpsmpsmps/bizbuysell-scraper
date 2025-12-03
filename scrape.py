import os
import json
import requests
import feedparser
import gspread
from google.oauth2.service_account import Credentials

# --- CONFIGURE YOUR SHEET ---
SHEET_NAME = "BizBuySell — Listings"  # Name of the Google Sheet
TAB_NAME = "BizBuySell"               # Name of the sheet tab


def get_bizbuysell_rss():
    """
    Fetch BizBuySell RSS feed through a proxy because BizBuySell blocks many cloud IPs.
    Try AllOrigins first, then Codetabs as a fallback.
    """
    urls = [
        "https://api.allorigins.win/raw?url=https://www.bizbuysell.com/rss/listings/",
        "https://api.codetabs.com/v1/proxy/?quest=https://www.bizbuysell.com/rss/listings/",
    ]

    last_error = None
    for proxy_url in urls:
        print(f"Trying proxy: {proxy_url}")
        try:
            response = requests.get(proxy_url, timeout=20)
            print("Status code:", response.status_code)
            if response.status_code != 200:
                last_error = f"Status {response.status_code}"
                continue

            xml = response.text
            feed = feedparser.parse(xml)
            if not feed.entries:
                last_error = "No entries in feed"
                continue

            print(f"Fetched {len(feed.entries)} entries from proxy.")
            return feed.entries
        except Exception as e:
            last_error = str(e)
            print("Error fetching via proxy:", e)

    raise Exception(f"Failed to fetch RSS via proxies. Last error: {last_error}")


def authorize_gsheet():
    """
    Authorize Google Sheets using the service account key
    stored in GitHub Actions secret.
    """
    if "GOOGLE_SERVICE_ACCOUNT_JSON" not in os.environ:
        raise RuntimeError("GOOGLE_SERVICE_ACCOUNT_JSON environment variable is missing")

    service_account_info = json.loads(os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"])
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    credentials = Credentials.from_service_account_info(
        service_account_info, scopes=scopes
    )
    client = gspread.authorize(credentials)
    return client


def write_rows_to_sheet(rows):
    """
    Write rows to Google Sheet, replacing old data.
    """
    client = authorize_gsheet()
    sheet = client.open(SHEET_NAME).worksheet(TAB_NAME)

    # Clear existing content
    sheet.clear()

    # Write rows
    sheet.update(rows)


def main():
    print("Fetching BizBuySell listings...")
    entries = get_bizbuysell_rss()

    # Header row
    rows = [["Title", "Link", "Description", "Published"]]

    for item in entries:
        title = item.get("title", "")
        link = item.get("link", "")
        desc = item.get("description", "")
        pub = item.get("published", "")

        rows.append([title, link, desc, pub])

    print(f"Prepared {len(rows)-1} listings to write.")
    write_rows_to_sheet(rows)
    print("Done! Data written to Google Sheet.")


if __name__ == "__main__":
    main()
