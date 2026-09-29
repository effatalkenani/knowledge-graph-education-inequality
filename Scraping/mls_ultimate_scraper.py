#!/usr/bin/env python3
"""
My Local School Data Scraper
============================

Student:
    Afaf Alhajjaji

Project:
    Education Inequality Spatial Analysis with Qualitative Place
    Knowledge Graphs

Purpose:
    Collect additional school information from the My Local School Wales
    website for integration into the Qualitative Place Knowledge Graph
    developed for the MSc dissertation.

Process:
    1. Read school identifiers from school_list.json.
    2. Construct the detail-page URL for each school.
    3. Download or reuse a cached copy of each school page.
    4. Extract school characteristics and summary statistics.
    5. Save each completed record to a JSON Lines checkpoint.
    6. Export the collected records to CSV.

Input:
    school_list.json

Outputs:
    mls_output/html_cache/<school_code>.html
    mls_output/schools.jsonl
    mls_output/welsh_schools_data_full.csv

Usage:
    python mls_ultimate_scraper.py

Optional limited run:
    python mls_ultimate_scraper.py --limit 10

Dependencies:
    requests
    beautifulsoup4
    pandas
"""

import argparse
import json
import re
import sys
import time
import os
from pathlib import Path
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup
import pandas as pd


# =================================================================
# Website and output configuration
# =================================================================

BASE = "https://mylocalschool.gov.wales"
SEARCH_URL = BASE + "/Schools/SchoolSearch?lang=en"
DETAIL_URL = BASE + "/School/{code}?lang=en"
SCHOOL_TYPES = ["Nursery", "Primary", "Middle", "Secondary", "Special"]

# Output directory, page cache, checkpoint and final CSV paths.
OUT_DIR = Path("mls_output")
CACHE_DIR = OUT_DIR / "html_cache"
LINKS_FILE = OUT_DIR / "school_links.json"
CHECKPOINT = OUT_DIR / "schools.jsonl"
CSV_FILE = OUT_DIR / "welsh_schools_data_full.csv"

# Delay between page requests and minimum number of fields required
# for accepting the structured parser result.
DELAY = 1.0
MIN_FIELDS_STRUCTURED = 4

# Request headers identify the academic purpose of the scraper
# and request the English-language version of each page.
HEADERS = {
    "User-Agent": "MSc-research-scraper (Cardiff University dissertation; contact via university email)",
    "Accept-Language": "en-GB,en;q=0.9",
}

# Labels expected within the school-detail section.
FIELD_LABELS = [
    "Local Authority",
    "Type",
    "Gender Mix",
    "Language",
    "Address",
    "Telephone"
]

# Labels expected within the school summary statistics.
SUMMARY_CAPTIONS = {
    "Number of pupils": "pupils",
    "Free school meals": "fsm_pct_3yr_avg",
    "Pupil Teacher Ratio": "ptr",
    "% Attendance during the year": "attendance_pct",
    "School budget per pupil": "budget_per_pupil",
    "Capped 9 points score": "capped_9",
    "Literacy points score": "literacy",
    "Numeracy points score": "numeracy",
    "Science points score": "science"
}

# Regular expression used to identify a UK postcode within an address.
POSTCODE_RE = re.compile(r"[A-Z]{1,2}\d{1,2}[A-Z]?\s*\d[A-Z]{2}")


# -----------------------------------------------------------------
# Fetching
# -----------------------------------------------------------------

def fetch_requests(url, session):
    """
    Retrieve a school-detail page.

    Args:
        url:
            URL of the school-detail page.
        session:
            Reusable requests session.

    Returns:
        The retrieved page as HTML text.

    Raises:
        requests.HTTPError:
            If the server returns an unsuccessful HTTP response.
    """
    r = session.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r.text


# -----------------------------------------------------------------
# Parsers
# -----------------------------------------------------------------

def parse_structured(soup):
    """
    Extract school information using the page's HTML structure.

    The parser reads labelled school details, summary statistics,
    the address and telephone number using the relevant HTML classes
    and element identifiers.

    Args:
        soup:
            BeautifulSoup representation of the school-detail page.

    Returns:
        A dictionary containing the fields found on the page.
    """
    data = {}

    # Extract the main labelled school characteristics.
    basic = soup.find("div", class_="school-details__basic-details")
    if basic:
        for pair in basic.find_all("div", class_="key-value-pair"):
            k = pair.find("div", class_="key-value-pair__key")
            v = pair.find("div", class_="key-value-pair__value")
            if k and v:
                data[k.text.strip()] = v.text.strip()

    # Extract the statistics displayed in the Summary section.
    summary = soup.find("div", id="Summary")
    if summary:
        for block in summary.find_all("div", class_="statistic-block"):
            v = block.find("div", class_="statistic-value")
            n = block.find("div", class_="statistic-name")
            if v and n:
                data[n.text.strip()] = v.text.strip()

    # Combine the separate address elements into one value.
    contact = soup.find("div", class_="school-details__contact")
    if contact:
        addr = contact.find("div", class_="school-details__address")
        if addr:
            parts = [
                d.text.strip()
                for d in addr.find_all("div")
                if d.text.strip()
            ]
            data["Address"] = ", ".join(parts)

    # Extract the displayed telephone number.
    tel = soup.find("a", href=re.compile(r"tel:"))
    if tel:
        data["Telephone"] = tel.text.strip()

    return data


def parse_linebased(soup, text):
    """
    Extract school information using a line-based fallback method.

    This parser is used when the structured parser returns too few
    fields. It searches the visible page text for known field labels
    and summary captions.

    Args:
        soup:
            BeautifulSoup representation of the page. Retained as part
            of the original parser interface.
        text:
            Visible page text separated into lines.

    Returns:
        A dictionary containing the fields found in the page text.
    """
    data = {}
    lines = [ln.strip() for ln in text.split("\n") if ln.strip()]

    # For ordinary fields, the value is expected on the following line.
    for i, ln in enumerate(lines[:-1]):
        if ln in FIELD_LABELS:
            data[ln] = lines[i + 1]

    # For summary statistics, the value is expected on the preceding line.
    for i, ln in enumerate(lines):
        for caption, key in SUMMARY_CAPTIONS.items():
            if ln.startswith(caption) and i > 0:
                data[caption] = lines[i - 1]

    return data


def parse_detail(html, url):
    """
    Convert one school-detail page into a structured record.

    The function first attempts structured HTML extraction. If fewer
    than four fields are returned, it uses the line-based fallback
    parser. It also extracts the school name, reference number,
    source URL and postcode.

    Args:
        html:
            HTML content of the school-detail page.
        url:
            Source URL of the school-detail page.

    Returns:
        A dictionary containing the extracted school record.
    """
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text("\n")
    row = {"url": url}

    # Extract the school name from the main page heading.
    h1 = soup.find("h1")
    row["school_name"] = h1.get_text(strip=True) if h1 else None

    # Extract the numeric school reference displayed on the page.
    m = re.search(r"Ref:\s*(\d+)", text)
    row["ref"] = m.group(1) if m else None

    # Use the structured parser when sufficient fields are found.
    # Otherwise, use the text-based fallback parser.
    data = parse_structured(soup)
    if len(data) >= MIN_FIELDS_STRUCTURED:
        row["parser_used"] = "structured"
    else:
        data = parse_linebased(soup, text)
        row["parser_used"] = "linebased"

    row.update(data)

    # Identify the postcode within the extracted address.
    addr = row.get("Address", "")
    pc = POSTCODE_RE.search(addr)
    row["postcode"] = pc.group(0) if pc else None

    return row


# -----------------------------------------------------------------
# Main pipeline
# -----------------------------------------------------------------

def main():
    """
    Run the school data-collection pipeline.

    The pipeline loads school identifiers, excludes records already
    present in the checkpoint, retrieves or reuses each HTML page,
    parses the school information and exports the accumulated records
    to CSV.
    """
    # Optional limit supports small test runs without processing
    # every remaining school.
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    # Create the output and cache directories when they do not exist.
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    # Use the school list produced by extract_school_list.py.
    if os.path.exists("school_list.json"):
        with open("school_list.json", "r") as f:
            schools = json.load(f)

        # Construct one detail-page URL for each school code.
        links = {
            str(s['schoolCode']): {
                "name": s['name'],
                "url": DETAIL_URL.format(code=s['schoolCode'])
            }
            for s in schools
        }
    else:
        print(
            "Please run extract_school_list.py first "
            "to generate school_list.json"
        )
        return

    # Read the checkpoint and identify previously processed schools.
    # These schools are skipped when the script is run again.
    done = set()
    if CHECKPOINT.exists():
        with open(CHECKPOINT, "r") as f:
            for line in f:
                done.add(json.loads(line).get("_key"))

    session = requests.Session()

    # Retain only schools that are not already in the checkpoint.
    todo = [
        (k, v)
        for k, v in links.items()
        if k not in done
    ]

    if args.limit:
        todo = todo[:args.limit]

    print(f"Starting harvest for {len(todo)} schools...")

    # Append each completed record immediately to preserve progress
    # if the collection process is interrupted.
    with open(CHECKPOINT, "a") as ckpt:
        for n, (key, info) in enumerate(todo, 1):
            cache_path = CACHE_DIR / f"{key}.html"

            try:
                # Reuse a cached page where available. Otherwise,
                # retrieve and cache it before parsing.
                if cache_path.exists():
                    html = cache_path.read_text()
                else:
                    html = fetch_requests(info["url"], session)
                    cache_path.write_text(html)
                    time.sleep(DELAY)

                # Parse the page and retain the school code as
                # the checkpoint key.
                row = parse_detail(html, info["url"])
                row["_key"] = key

                # Write one JSON object per line to support resumption.
                ckpt.write(json.dumps(row) + "\n")
                ckpt.flush()

                print(
                    f"[{n}/{len(todo)}] Processed: "
                    f"{row.get('school_name')} "
                    f"(Parser: {row['parser_used']})"
                )

            except Exception as e:
                # Report the individual failure and continue with
                # the remaining schools.
                print(f"Error processing {key}: {e}")

    # Export all accumulated checkpoint records to the final CSV file.
    if CHECKPOINT.exists():
        rows = []
        with open(CHECKPOINT, "r") as f:
            for line in f:
                rows.append(json.loads(line))

        pd.DataFrame(rows).to_csv(
            CSV_FILE,
            index=False,
            encoding="utf-8-sig"
        )
        print(f"Exported {len(rows)} schools to {CSV_FILE}")


if __name__ == "__main__":
    main()