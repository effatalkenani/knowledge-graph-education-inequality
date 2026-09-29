"""
School List Extractor
=====================

Student:
    Afaf Alhajjaji

Project:
    Education Inequality Spatial Analysis with Qualitative Place
    Knowledge Graphs

Purpose:
    Extract the complete list of Welsh schools from a saved
    My Local School search-results page.

Description:
    The My Local School search page stores its school results as
    HTML-encoded JSON inside a hidden input element named
    ``schoolResults``. This script reads the saved HTML page,
    locates that element, decodes its value and writes the resulting
    school records to ``school_list.json``.

    The generated JSON file provides the school codes and names
    required by ``mls_ultimate_scraper.py`` to construct and process
    the individual school-detail URLs.

Input:
    search_page.html

Output:
    school_list.json

Usage:
    python extract_school_list.py

Dependencies:
    Python standard library only
"""

import json
import re


def extract_schools():
    """
    Extract the school list embedded in the saved search page.

    The function searches for the hidden ``schoolResults`` input,
    decodes the HTML entities contained in its value and converts
    the resulting JSON text into Python objects.

    Returns:
        A list containing the extracted school records.

        An empty list is returned if the hidden input cannot be
        found or if an error occurs while reading or decoding
        the source file.
    """
    try:
        # Open the locally saved My Local School search-results page.
        with open("search_page.html", "r", encoding="utf-8") as f:
            content = f.read()
        
        # Look for the hidden input value that contains the JSON list of schools.
        match = re.search(
            r'id="schoolResults" type="hidden" value="(.*?)"',
            content
        )

        if match:
            # The captured value contains HTML-encoded JSON.
            encoded_json = match.group(1)

            # Import the standard-library HTML utility used to decode
            # character entities in the captured value.
            import html

            # Convert HTML entities back to their original characters.
            decoded_json = html.unescape(encoded_json)
            
            # Parse the decoded JSON into a list of school records.
            schools = json.loads(decoded_json)
            print(
                f"Successfully extracted "
                f"{len(schools)} schools."
            )
            
            # Write the extracted school list in a readable JSON format.
            with open(
                "school_list.json",
                "w",
                encoding="utf-8"
            ) as out:
                json.dump(schools, out, indent=4)
            
            return schools

        else:
            # Report that the expected hidden element was not present.
            print(
                "Could not find schoolResults hidden input."
            )
            return []

    except Exception as e:
        # Report file-reading, matching or JSON-decoding errors
        # without terminating with an unhandled exception.
        print(f"Error: {e}")
        return []


if __name__ == "__main__":
    # Execute the extraction when the file is run directly.
    extract_schools()