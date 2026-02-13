#!/usr/bin/env python3
"""
Build the routing graph from raw OSM data and elevation data.

Reads:
  .tmp/raw_pistes.json
  .tmp/raw_lifts.json
  .tmp/elevations.json

Outputs:
  app/data/graph.json    - Routing graph (nodes + edges)
  app/data/stations.json - Station metadata
"""

import json
import math
import os
import sys
from collections import defaultdict

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TMP_DIR = os.path.join(BASE_DIR, ".tmp")
DATA_DIR = os.path.join(BASE_DIR, "app", "data")

# Spatial clustering radius in meters
CLUSTER_RADIUS_M = 75

# OSM difficulty -> French color mapping
DIFFICULTY_MAP = {
    "novice": "green",
    "easy": "blue",
    "intermediate": "red",
    "advanced": "black",
    "expert": "black",
    "freeride": "black",
}

# Known La Plagne stations with approximate coordinates
STATIONS = [
    {"name": "Plagne Centre", "lat": 45.5070, "lon": 6.6770, "ele": 1970},
    {"name": "Aime-La Plagne", "lat": 45.5110, "lon": 6.6740, "ele": 2100},
    {"name": "Belle Plagne", "lat": 45.5090, "lon": 6.6680, "ele": 2050},
    {"name": "Plagne Bellecote", "lat": 45.5050, "lon": 6.6610, "ele": 1930},
    {"name": "Plagne Soleil", "lat": 45.5130, "lon": 6.6630, "ele": 2050},
    {"name": "Plagne Villages", "lat": 45.5130, "lon": 6.6680, "ele": 2050},
    {"name": "Plagne 1800", "lat": 45.5010, "lon": 6.6840, "ele": 1800},
    {"name": "Champagny", "lat": 45.4630, "lon": 6.7270, "ele": 1250},
    {"name": "Montchavin", "lat": 45.5340, "lon": 6.6420, "ele": 1250},
    {"name": "Les Coches", "lat": 45.5230, "lon": 6.6380, "ele": 1450},
    {"name": "Montalbert", "lat": 45.4880, "lon": 6.6580, "ele": 1350},
]


def haversine_m(lat1, lon1, lat2, lon2):
    """Calculate distance in meters between two coordinates."""
    R = 6371000  # Earth radius in meters
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon / 2) ** 2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def calculate_path_distance(geometry):
    """Calculate total distance along a path of coordinates in meters."""
    total = 0
    for i in range(1, len(geometry)):
        total += haversine_m(
            geometry[i - 1]["lat"], geometry[i - 1]["lon"],
            geometry[i]["lat"], geometry[i]["lon"]
        )
    return total


def round_coord(val, decimals=5):
    return round(val, decimals)


def get_elevation(lat, lon, elevations):
    """Look up elevation for a coordinate."""
    key = f"{round_coord(lat)},{round_coord(lon)}"
    return elevations.get(key, None)


def parse_pistes(raw_data, elevations):
    """Parse piste elements from raw OSM data."""
    pistes = []
    relation_way_ids = set()

    elements = raw_data.get("elements", [])

    # First pass: collect way IDs that belong to relations
    for element in elements:
        if element.get("type") == "relation":
            for member in element.get("members", []):
                if member.get("type") == "way":
                    relation_way_ids.add(member.get("ref"))

    # Second pass: process elements
    for element in elements:
        tags = element.get("tags", {})
        piste_type = tags.get("piste:type", "downhill")

        # Skip standalone ways that belong to a relation (avoid duplicates)
        if element.get("type") == "way" and element.get("id") in relation_way_ids:
            continue

        geom = element.get("geometry", [])

        # For relations, try to reconstruct geometry from members
        if element.get("type") == "relation" and not geom:
            geom = reconstruct_relation_geometry(element, elements)

        if not geom or len(geom) < 2:
            continue

        name = tags.get("name", tags.get("ref", ""))
        difficulty_raw = tags.get("piste:difficulty", "")
        difficulty = DIFFICULTY_MAP.get(difficulty_raw, "blue")  # Default to blue

        first = geom[0]
        last = geom[-1]

        ele_first = get_elevation(first["lat"], first["lon"], elevations)
        ele_last = get_elevation(last["lat"], last["lon"], elevations)

        if ele_first is None or ele_last is None:
            continue

        distance = calculate_path_distance(geom)

        # Determine direction: slopes go downhill (high to low)
        if ele_first >= ele_last:
            top = {"lat": first["lat"], "lon": first["lon"], "ele": ele_first}
            bottom = {"lat": last["lat"], "lon": last["lon"], "ele": ele_last}
            geom_ordered = geom
        else:
            top = {"lat": last["lat"], "lon": last["lon"], "ele": ele_last}
            bottom = {"lat": first["lat"], "lon": first["lon"], "ele": ele_first}
            geom_ordered = list(reversed(geom))

        is_connection = piste_type == "connection"

        piste = {
            "id": f"piste_{element['id']}",
            "osm_id": element["id"],
            "name": name,
            "type": "slope",
            "piste_type": piste_type,
            "difficulty": difficulty if not is_connection else "blue",
            "is_connection": is_connection,
            "top": top,
            "bottom": bottom,
            "distance": round(distance),
            "elevation_delta": round(top["ele"] - bottom["ele"]),
            "geometry": [{"lat": round_coord(p["lat"]), "lon": round_coord(p["lon"])} for p in geom_ordered],
        }
        pistes.append(piste)

    return pistes


def reconstruct_relation_geometry(relation, all_elements):
    """Try to reconstruct geometry from relation members."""
    # Build a map of way_id -> element for quick lookup
    way_map = {}
    for el in all_elements:
        if el.get("type") == "way":
            way_map[el["id"]] = el

    geom = []
    for member in relation.get("members", []):
        if member.get("type") == "way" and member.get("geometry"):
            geom.extend(member["geometry"])
        elif member.get("type") == "way" and member.get("ref") in way_map:
            way = way_map[member["ref"]]
            if way.get("geometry"):
                geom.extend(way["geometry"])

    return geom


def parse_lifts(raw_data, elevations):
    """Parse lift elements from raw OSM data."""
    lifts = []

    for element in raw_data.get("elements", []):
        if element.get("type") != "way":
            continue

        tags = element.get("tags", {})
        aerialway = tags.get("aerialway", "")

        # Skip non-transport aerialways
        if aerialway in ("pylon", "station", "goods", "zip_line", ""):
            continue

        geom = element.get("geometry", [])
        if not geom or len(geom) < 2:
            continue

        name = tags.get("name", tags.get("ref", ""))

        first = geom[0]
        last = geom[-1]

        ele_first = get_elevation(first["lat"], first["lon"], elevations)
        ele_last = get_elevation(last["lat"], last["lon"], elevations)

        if ele_first is None or ele_last is None:
            continue

        distance = calculate_path_distance(geom)

        # Lifts go uphill (low to high)
        if ele_first <= ele_last:
            bottom = {"lat": first["lat"], "lon": first["lon"], "ele": ele_first}
            top = {"lat": last["lat"], "lon": last["lon"], "ele": ele_last}
            geom_ordered = geom
        else:
            bottom = {"lat": last["lat"], "lon": last["lon"], "ele": ele_last}
            top = {"lat": first["lat"], "lon": first["lon"], "ele": ele_first}
            geom_ordered = list(reversed(geom))

        # Map aerialway types to categories
        lift_type_map = {
            "cable_car": "cable_car",
            "gondola": "gondola",
            "mixed_lift": "gondola",
            "chair_lift": "chair_lift",
            "drag_lift": "drag_lift",
            "t-bar": "drag_lift",
            "j-bar": "drag_lift",
            "platter": "drag_lift",
            "rope_tow": "drag_lift",
            "magic_carpet": "magic_carpet",
            "funicular": "gondola",
        }
        lift_type = lift_type_map.get(aerialway, "chair_lift")

        lift = {
            "id": f"lift_{element['id']}",
            "osm_id": element["id"],
            "name": name,
            "type": "lift",
            "lift_type": lift_type,
            "aerialway": aerialway,
            "bottom": bottom,
            "top": top,
            "distance": round(distance),
            "elevation_delta": round(top["ele"] - bottom["ele"]),
            "geometry": [{"lat": round_coord(p["lat"]), "lon": round_coord(p["lon"])} for p in geom_ordered],
        }
        lifts.append(lift)

    return lifts


def cluster_endpoints(pistes, lifts):
    """
    Cluster all endpoints within CLUSTER_RADIUS_M into single nodes.
    Returns:
      nodes: dict of node_id -> {lat, lon, ele, station}
      endpoint_to_node: dict of "lat,lon" -> node_id
    """
    # Collect all endpoints
    endpoints = []
    for piste in pistes:
        endpoints.append((piste["top"]["lat"], piste["top"]["lon"], piste["top"]["ele"]))
        endpoints.append((piste["bottom"]["lat"], piste["bottom"]["lon"], piste["bottom"]["ele"]))
    for lift in lifts:
        endpoints.append((lift["bottom"]["lat"], lift["bottom"]["lon"], lift["bottom"]["ele"]))
        endpoints.append((lift["top"]["lat"], lift["top"]["lon"], lift["top"]["ele"]))

    # Sort by latitude for efficient clustering
    endpoints.sort(key=lambda p: p[0])

    # Greedy clustering
    clustered = [False] * len(endpoints)
    clusters = []

    for i in range(len(endpoints)):
        if clustered[i]:
            continue

        cluster = [i]
        clustered[i] = True

        for j in range(i + 1, len(endpoints)):
            if clustered[j]:
                continue

            # Quick latitude check (skip if too far in lat)
            if abs(endpoints[j][0] - endpoints[i][0]) > 0.001:  # ~111m
                break

            dist = haversine_m(endpoints[i][0], endpoints[i][1],
                               endpoints[j][0], endpoints[j][1])
            if dist <= CLUSTER_RADIUS_M:
                cluster.append(j)
                clustered[j] = True

        clusters.append(cluster)

    # Build nodes from clusters
    nodes = {}
    endpoint_to_node = {}

    for idx, cluster in enumerate(clusters):
        node_id = f"n{idx}"

        # Centroid
        avg_lat = sum(endpoints[i][0] for i in cluster) / len(cluster)
        avg_lon = sum(endpoints[i][1] for i in cluster) / len(cluster)
        avg_ele = sum(endpoints[i][2] for i in cluster) / len(cluster)

        nodes[node_id] = {
            "lat": round_coord(avg_lat),
            "lon": round_coord(avg_lon),
            "ele": round(avg_ele),
            "station": None,
        }

        # Map all cluster member coordinates to this node
        for i in cluster:
            key = f"{round_coord(endpoints[i][0])},{round_coord(endpoints[i][1])}"
            endpoint_to_node[key] = node_id

    return nodes, endpoint_to_node


def assign_stations(nodes):
    """Assign station names to the nearest graph nodes."""
    assigned = []

    for station in STATIONS:
        best_node = None
        best_dist = float("inf")

        for node_id, node in nodes.items():
            dist = haversine_m(station["lat"], station["lon"], node["lat"], node["lon"])
            if dist < best_dist:
                best_dist = dist
                best_node = node_id

        if best_node and best_dist < 500:  # Within 500m
            nodes[best_node]["station"] = station["name"]
            assigned.append({
                "name": station["name"],
                "nodeId": best_node,
                "lat": nodes[best_node]["lat"],
                "lon": nodes[best_node]["lon"],
                "ele": nodes[best_node]["ele"],
                "distance_from_ref": round(best_dist),
            })
            print(f"  Station '{station['name']}' -> node {best_node} ({best_dist:.0f}m away)")
        else:
            print(f"  WARNING: Station '{station['name']}' not matched (nearest: {best_dist:.0f}m)")

    return assigned


def build_edges(pistes, lifts, endpoint_to_node):
    """Build directed edges from pistes and lifts."""
    edges = []

    for piste in pistes:
        top_key = f"{round_coord(piste['top']['lat'])},{round_coord(piste['top']['lon'])}"
        bottom_key = f"{round_coord(piste['bottom']['lat'])},{round_coord(piste['bottom']['lon'])}"

        source_node = endpoint_to_node.get(top_key)
        target_node = endpoint_to_node.get(bottom_key)

        if not source_node or not target_node:
            continue

        if source_node == target_node:
            continue  # Skip self-loops

        edge = {
            "id": piste["id"],
            "source": source_node,
            "target": target_node,
            "name": piste["name"],
            "type": "slope",
            "difficulty": piste["difficulty"],
            "distance": piste["distance"],
            "elevationDelta": -piste["elevation_delta"],  # Negative = going down
            "geometry": [[p["lat"], p["lon"]] for p in piste["geometry"]],
        }
        edges.append(edge)

        # Connection pistes are bidirectional
        if piste["is_connection"]:
            reverse_edge = {
                "id": piste["id"] + "_rev",
                "source": target_node,
                "target": source_node,
                "name": piste["name"],
                "type": "slope",
                "difficulty": piste["difficulty"],
                "distance": piste["distance"],
                "elevationDelta": piste["elevation_delta"],
                "geometry": [[p["lat"], p["lon"]] for p in reversed(piste["geometry"])],
            }
            edges.append(reverse_edge)

    for lift in lifts:
        bottom_key = f"{round_coord(lift['bottom']['lat'])},{round_coord(lift['bottom']['lon'])}"
        top_key = f"{round_coord(lift['top']['lat'])},{round_coord(lift['top']['lon'])}"

        source_node = endpoint_to_node.get(bottom_key)
        target_node = endpoint_to_node.get(top_key)

        if not source_node or not target_node:
            continue

        if source_node == target_node:
            continue

        edge = {
            "id": lift["id"],
            "source": source_node,
            "target": target_node,
            "name": lift["name"],
            "type": "lift",
            "liftType": lift["lift_type"],
            "distance": lift["distance"],
            "elevationDelta": lift["elevation_delta"],  # Positive = going up
            "geometry": [[p["lat"], p["lon"]] for p in lift["geometry"]],
        }
        edges.append(edge)

    return edges


def analyze_connectivity(nodes, edges):
    """Analyze graph connectivity using BFS."""
    # Build adjacency list (considering both directions for reachability)
    adj = defaultdict(set)
    for edge in edges:
        adj[edge["source"]].add(edge["target"])
        adj[edge["target"]].add(edge["source"])

    # Find connected components
    visited = set()
    components = []

    for node_id in nodes:
        if node_id in visited:
            continue

        component = set()
        queue = [node_id]
        while queue:
            current = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)
            component.add(current)
            for neighbor in adj.get(current, set()):
                if neighbor not in visited:
                    queue.append(neighbor)

        components.append(component)

    return components


def main():
    os.makedirs(DATA_DIR, exist_ok=True)

    piste_file = os.path.join(TMP_DIR, "raw_pistes.json")
    lift_file = os.path.join(TMP_DIR, "raw_lifts.json")
    elevation_file = os.path.join(TMP_DIR, "elevations.json")

    for f in [piste_file, lift_file, elevation_file]:
        if not os.path.exists(f):
            print(f"Error: {f} not found. Run previous pipeline steps first.")
            sys.exit(1)

    print("=" * 60)
    print("Building routing graph")
    print("=" * 60)

    # Load data
    print("\n[1/6] Loading raw data...")
    with open(piste_file) as f:
        raw_pistes = json.load(f)
    with open(lift_file) as f:
        raw_lifts = json.load(f)
    with open(elevation_file) as f:
        elevations = json.load(f)
    print(f"  Loaded {len(raw_pistes.get('elements', []))} piste elements")
    print(f"  Loaded {len(raw_lifts.get('elements', []))} lift elements")
    print(f"  Loaded {len(elevations)} elevation points")

    # Parse pistes
    print("\n[2/6] Parsing pistes...")
    pistes = parse_pistes(raw_pistes, elevations)
    difficulty_counts = defaultdict(int)
    for p in pistes:
        difficulty_counts[p["difficulty"]] += 1
    print(f"  Parsed {len(pistes)} pistes")
    print(f"  Difficulty distribution: {dict(difficulty_counts)}")

    # Parse lifts
    print("\n[3/6] Parsing lifts...")
    lifts = parse_lifts(raw_lifts, elevations)
    lift_type_counts = defaultdict(int)
    for l in lifts:
        lift_type_counts[l["lift_type"]] += 1
    print(f"  Parsed {len(lifts)} lifts")
    print(f"  Lift types: {dict(lift_type_counts)}")

    # Cluster endpoints into nodes
    print(f"\n[4/6] Clustering endpoints (radius={CLUSTER_RADIUS_M}m)...")
    nodes, endpoint_to_node = cluster_endpoints(pistes, lifts)
    print(f"  Created {len(nodes)} nodes from clustering")

    # Assign stations
    print("\n[5/6] Assigning stations...")
    stations = assign_stations(nodes)
    print(f"  Assigned {len(stations)} stations")

    # Build edges
    print("\n[6/6] Building edges...")
    edges = build_edges(pistes, lifts, endpoint_to_node)
    slope_edges = sum(1 for e in edges if e["type"] == "slope")
    lift_edges = sum(1 for e in edges if e["type"] == "lift")
    print(f"  Created {len(edges)} edges ({slope_edges} slopes, {lift_edges} lifts)")

    # Connectivity analysis
    print("\n--- Connectivity Analysis ---")
    components = analyze_connectivity(nodes, edges)
    print(f"  Connected components: {len(components)}")
    for i, comp in enumerate(sorted(components, key=len, reverse=True)):
        station_names = [nodes[n]["station"] for n in comp if nodes[n].get("station")]
        print(f"  Component {i + 1}: {len(comp)} nodes, stations: {station_names or ['(none)']}")

    # Keep only the largest component
    if len(components) > 1:
        largest = max(components, key=len)
        removed_nodes = set()
        for comp in components:
            if comp != largest:
                removed_nodes.update(comp)

        nodes = {nid: n for nid, n in nodes.items() if nid not in removed_nodes}
        edges = [e for e in edges if e["source"] not in removed_nodes and e["target"] not in removed_nodes]
        print(f"\n  Kept largest component: {len(nodes)} nodes, {len(edges)} edges")
        print(f"  Removed {len(removed_nodes)} disconnected nodes")

    # Build graph JSON
    graph = {
        "nodes": nodes,
        "edges": edges,
        "metadata": {
            "generated": "2026-02-13",
            "slopeCount": slope_edges,
            "liftCount": lift_edges,
            "nodeCount": len(nodes),
            "edgeCount": len(edges),
            "boundingBox": {"south": 45.48, "north": 45.58, "west": 6.62, "east": 6.78},
        },
    }

    # Save graph
    graph_file = os.path.join(DATA_DIR, "graph.json")
    with open(graph_file, "w") as f:
        json.dump(graph, f)
    print(f"\n  Saved graph to {graph_file}")
    print(f"  File size: {os.path.getsize(graph_file) / 1024:.1f} KB")

    # Save stations
    stations_file = os.path.join(DATA_DIR, "stations.json")
    with open(stations_file, "w") as f:
        json.dump(stations, f, indent=2)
    print(f"  Saved stations to {stations_file}")

    print(f"\n{'=' * 60}")
    print("Graph build complete!")
    print(f"  Nodes: {len(nodes)}")
    print(f"  Edges: {len(edges)} ({slope_edges} slopes, {lift_edges} lifts)")
    print(f"  Stations: {len(stations)}")
    print("=" * 60)


if __name__ == "__main__":
    main()
