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
    Fetch BizBuySell RSS feed.
    """
    url = "https://www.bizbuysell.com/rss/listings/"
    feed = feedparser.parse(url)
    return feed.entries


def authorize_gsheet():
    """
    Authorize Google Sheets using the service account key
    stored in GitHub Actions secret.
    """
    service_account_info = json.loads(
        os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"]
    )
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

    print(f"Fetched {len(rows)-1} listings.")
    write_rows_to_sheet(rows)

    print("Done! Data written to Google Sheet.")


if __name__ == "__main__":
    import os
    main()
