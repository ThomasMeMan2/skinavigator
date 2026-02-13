#!/usr/bin/env python3
"""
Enrich ski area data with elevation information.

Reads raw piste and lift data from .tmp/, extracts all unique endpoint
coordinates, and fetches missing elevation data from Open Topo Data API.

Output:
  .tmp/elevations.json - Map of "lat,lon" -> elevation_meters
"""

import json
import math
import os
import sys
import time
import urllib.request
import urllib.error

TMP_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".tmp")

# Open Topo Data API (free, SRTM-based)
ELEVATION_API = "https://api.opentopodata.org/v1/srtm30m"
BATCH_SIZE = 100  # Max locations per request
REQUEST_DELAY = 1.1  # Seconds between requests (rate limit: 1 req/s)

# Fallback API
FALLBACK_API = "https://api.open-elevation.com/api/v1/lookup"


def round_coord(val, decimals=5):
    """Round coordinate to reduce duplicates."""
    return round(val, decimals)


def extract_endpoints(data_file):
    """Extract first and last coordinates from all ways in the data file."""
    with open(data_file, "r") as f:
        data = json.load(f)

    endpoints = set()
    for element in data.get("elements", []):
        geom = element.get("geometry", [])
        if not geom:
            # For relations, try to get geometry from members
            bounds = element.get("bounds", {})
            if bounds:
                continue  # Relations with bounds but no inline geometry
            continue

        # First and last points
        first = geom[0]
        last = geom[-1]
        endpoints.add((round_coord(first["lat"]), round_coord(first["lon"])))
        endpoints.add((round_coord(last["lat"]), round_coord(last["lon"])))

    return endpoints


def check_existing_elevations(data_file):
    """Check for elevation tags already present in OSM data."""
    with open(data_file, "r") as f:
        data = json.load(f)

    known = {}
    for element in data.get("elements", []):
        tags = element.get("tags", {})
        if "ele" in tags:
            try:
                ele = float(tags["ele"])
                geom = element.get("geometry", [])
                if geom:
                    # Associate elevation with first and last points
                    first = geom[0]
                    last = geom[-1]
                    # Lift stations often have elevation on the node
                    key_first = f"{round_coord(first['lat'])},{round_coord(first['lon'])}"
                    key_last = f"{round_coord(last['lat'])},{round_coord(last['lon'])}"
                    known[key_first] = ele
                    known[key_last] = ele
            except (ValueError, TypeError):
                pass

    return known


def fetch_elevations_batch(coords, api_url=ELEVATION_API):
    """Fetch elevations for a batch of coordinates."""
    locations = "|".join(f"{lat},{lon}" for lat, lon in coords)
    url = f"{api_url}?locations={locations}"

    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=30) as response:
        data = json.loads(response.read().decode("utf-8"))

    results = {}
    for result in data.get("results", []):
        lat = round_coord(result["location"]["lat"])
        lon = round_coord(result["location"]["lng"])
        ele = result.get("elevation")
        if ele is not None:
            results[f"{lat},{lon}"] = ele

    return results


def fetch_elevations_fallback(coords):
    """Fallback elevation API."""
    payload = json.dumps({
        "locations": [{"latitude": lat, "longitude": lon} for lat, lon in coords]
    })

    req = urllib.request.Request(
        FALLBACK_API,
        data=payload.encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )

    with urllib.request.urlopen(req, timeout=30) as response:
        data = json.loads(response.read().decode("utf-8"))

    results = {}
    for result in data.get("results", []):
        lat = round_coord(result["latitude"])
        lon = round_coord(result["longitude"])
        ele = result.get("elevation")
        if ele is not None:
            results[f"{lat},{lon}"] = ele

    return results


def main():
    piste_file = os.path.join(TMP_DIR, "raw_pistes.json")
    lift_file = os.path.join(TMP_DIR, "raw_lifts.json")
    output_file = os.path.join(TMP_DIR, "elevations.json")

    if not os.path.exists(piste_file) or not os.path.exists(lift_file):
        print("Error: Raw data files not found. Run fetch_osm_data.py first.")
        sys.exit(1)

    print("=" * 60)
    print("Enriching elevation data")
    print("=" * 60)

    # Collect all unique endpoints
    print("\n[1/4] Extracting endpoints from piste data...")
    piste_endpoints = extract_endpoints(piste_file)
    print(f"  Found {len(piste_endpoints)} unique piste endpoints")

    print("\n[2/4] Extracting endpoints from lift data...")
    lift_endpoints = extract_endpoints(lift_file)
    print(f"  Found {len(lift_endpoints)} unique lift endpoints")

    all_endpoints = piste_endpoints | lift_endpoints
    print(f"\n  Total unique endpoints: {len(all_endpoints)}")

    # Check for existing OSM elevation data
    print("\n[3/4] Checking existing OSM elevation tags...")
    known_elevations = {}
    known_elevations.update(check_existing_elevations(piste_file))
    known_elevations.update(check_existing_elevations(lift_file))
    print(f"  Found {len(known_elevations)} points with existing elevation data")

    # Determine which points still need elevation
    missing = []
    for lat, lon in all_endpoints:
        key = f"{lat},{lon}"
        if key not in known_elevations:
            missing.append((lat, lon))

    print(f"  Points needing elevation lookup: {len(missing)}")

    # Fetch missing elevations in batches
    print("\n[4/4] Fetching missing elevations from Open Topo Data...")
    fetched = {}

    if missing:
        batches = [missing[i:i + BATCH_SIZE] for i in range(0, len(missing), BATCH_SIZE)]
        print(f"  Processing {len(batches)} batches of up to {BATCH_SIZE} points...")

        for i, batch in enumerate(batches):
            try:
                print(f"  Batch {i + 1}/{len(batches)} ({len(batch)} points)...")
                result = fetch_elevations_batch(batch)
                fetched.update(result)
                print(f"    Got {len(result)} elevations")

                if i < len(batches) - 1:
                    time.sleep(REQUEST_DELAY)

            except Exception as e:
                print(f"    Primary API failed: {e}")
                print(f"    Trying fallback API...")
                try:
                    result = fetch_elevations_fallback(batch)
                    fetched.update(result)
                    print(f"    Fallback got {len(result)} elevations")
                except Exception as e2:
                    print(f"    Fallback also failed: {e2}")
                    print(f"    Skipping batch {i + 1}")

    # Merge all elevation data
    all_elevations = {**known_elevations, **fetched}

    # For any still-missing points, estimate from nearby known elevations
    still_missing = 0
    for lat, lon in all_endpoints:
        key = f"{lat},{lon}"
        if key not in all_elevations:
            still_missing += 1
            # Try to find nearest known elevation
            nearest_ele = find_nearest_elevation(lat, lon, all_elevations)
            if nearest_ele is not None:
                all_elevations[key] = nearest_ele
            else:
                # Default to a reasonable mid-mountain elevation
                all_elevations[key] = 2000.0
                print(f"  WARNING: No elevation found for ({lat}, {lon}), defaulting to 2000m")

    # Save
    with open(output_file, "w") as f:
        json.dump(all_elevations, f, indent=2)

    print(f"\n{'=' * 60}")
    print(f"Elevation data saved to {output_file}")
    print(f"  Total points: {len(all_elevations)}")
    print(f"  From OSM tags: {len(known_elevations)}")
    print(f"  From API: {len(fetched)}")
    print(f"  Estimated/default: {still_missing}")

    # Print elevation range
    elevations = list(all_elevations.values())
    if elevations:
        print(f"  Elevation range: {min(elevations):.0f}m - {max(elevations):.0f}m")
    print("=" * 60)


def find_nearest_elevation(lat, lon, known_elevations, max_distance_km=1.0):
    """Find the nearest known elevation within max_distance_km."""
    best_ele = None
    best_dist = float("inf")

    for key, ele in known_elevations.items():
        parts = key.split(",")
        klat, klon = float(parts[0]), float(parts[1])
        dist = haversine(lat, lon, klat, klon)
        if dist < best_dist and dist < max_distance_km:
            best_dist = dist
            best_ele = ele

    return best_ele


def haversine(lat1, lon1, lat2, lon2):
    """Calculate distance in km between two coordinates."""
    R = 6371  # Earth radius in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon / 2) ** 2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


if __name__ == "__main__":
    main()
