#!/usr/bin/env python3
"""
Fetch La Plagne ski area data from OpenStreetMap Overpass API.

Queries:
  1. Downhill pistes (piste:type=downhill) with full geometry
  2. Connection pistes (piste:type=connection) for flat traversals
  3. Aerialways (lifts) with full geometry

Output:
  .tmp/raw_pistes.json  - Raw piste data
  .tmp/raw_lifts.json   - Raw lift data
"""

import json
import os
import sys
import time
import urllib.request
import urllib.error
import urllib.parse

OVERPASS_URL = "https://overpass-api.de/api/interpreter"

# La Plagne bounding box
BBOX = "45.48,6.62,45.58,6.78"

TMP_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".tmp")


def query_overpass(query, description="data", max_retries=3):
    """Execute an Overpass API query with retry logic."""
    encoded = urllib.parse.urlencode({"data": query})

    for attempt in range(max_retries):
        try:
            timeout = 120 + (attempt * 60)  # Increase timeout each retry
            print(f"  Fetching {description} (attempt {attempt + 1}/{max_retries}, timeout={timeout}s)...")

            req = urllib.request.Request(
                OVERPASS_URL,
                data=encoded.encode("utf-8"),
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )

            with urllib.request.urlopen(req, timeout=timeout) as response:
                raw = response.read().decode("utf-8")
                data = json.loads(raw)

                elements = data.get("elements", [])
                print(f"  Got {len(elements)} elements for {description}")
                return data

        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as e:
            print(f"  Attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                wait = 10 * (attempt + 1)
                print(f"  Waiting {wait}s before retry...")
                time.sleep(wait)
            else:
                print(f"  All {max_retries} attempts failed for {description}")
                raise


def fetch_pistes():
    """Fetch all downhill pistes and connection pistes."""
    query = f"""
[out:json][timeout:120];
(
  way["piste:type"="downhill"]({BBOX});
  relation["piste:type"="downhill"]({BBOX});
  way["piste:type"="connection"]({BBOX});
);
out geom;
"""
    return query_overpass(query, "pistes (downhill + connection)")


def fetch_lifts():
    """Fetch all aerialway features (ski lifts)."""
    query = f"""
[out:json][timeout:120];
(
  way["aerialway"]({BBOX});
);
out geom;
"""
    return query_overpass(query, "lifts (aerialways)")


def main():
    os.makedirs(TMP_DIR, exist_ok=True)

    print("=" * 60)
    print("Fetching La Plagne ski data from OpenStreetMap")
    print(f"Bounding box: {BBOX}")
    print("=" * 60)

    # Fetch pistes
    print("\n[1/2] Fetching pistes...")
    piste_data = fetch_pistes()
    piste_file = os.path.join(TMP_DIR, "raw_pistes.json")
    with open(piste_file, "w") as f:
        json.dump(piste_data, f, indent=2)

    piste_elements = piste_data.get("elements", [])
    downhill = sum(1 for e in piste_elements if e.get("tags", {}).get("piste:type") == "downhill")
    connection = sum(1 for e in piste_elements if e.get("tags", {}).get("piste:type") == "connection")
    print(f"  Saved: {piste_file}")
    print(f"  Downhill: {downhill}, Connection: {connection}")

    # Fetch lifts
    print("\n[2/2] Fetching lifts...")
    lift_data = fetch_lifts()
    lift_file = os.path.join(TMP_DIR, "raw_lifts.json")
    with open(lift_file, "w") as f:
        json.dump(lift_data, f, indent=2)

    lift_elements = lift_data.get("elements", [])
    lift_types = {}
    for e in lift_elements:
        lt = e.get("tags", {}).get("aerialway", "unknown")
        lift_types[lt] = lift_types.get(lt, 0) + 1
    print(f"  Saved: {lift_file}")
    print(f"  Lift types: {lift_types}")

    # Summary
    print("\n" + "=" * 60)
    print("Summary:")
    print(f"  Total pistes: {len(piste_elements)} ({downhill} downhill, {connection} connection)")
    print(f"  Total lifts: {len(lift_elements)}")
    print("=" * 60)


if __name__ == "__main__":
    main()
