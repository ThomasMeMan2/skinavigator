#!/usr/bin/env python3
"""
Validate the routing graph for connectivity and quality.

Reads:
  app/data/graph.json
  app/data/stations.json

Checks:
  - Connected components (should be 1 for main ski area)
  - Station-to-station reachability (directed)
  - Node degree distribution
  - Edge quality (zero distance, extreme elevations, etc.)
"""

import json
import os
import sys
from collections import defaultdict

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "app", "data")


def load_graph():
    graph_file = os.path.join(DATA_DIR, "graph.json")
    stations_file = os.path.join(DATA_DIR, "stations.json")

    if not os.path.exists(graph_file):
        print(f"Error: {graph_file} not found")
        sys.exit(1)

    with open(graph_file) as f:
        graph = json.load(f)
    with open(stations_file) as f:
        stations = json.load(f)

    return graph, stations


def check_directed_reachability(nodes, edges, stations):
    """Check if all stations are reachable from each other using directed edges."""
    # Build directed adjacency list
    adj = defaultdict(set)
    for edge in edges:
        adj[edge["source"]].add(edge["target"])

    results = []
    station_ids = [s["nodeId"] for s in stations]

    for s1 in stations:
        for s2 in stations:
            if s1["nodeId"] == s2["nodeId"]:
                continue

            # BFS from s1 to s2
            visited = set()
            queue = [s1["nodeId"]]
            found = False

            while queue:
                current = queue.pop(0)
                if current == s2["nodeId"]:
                    found = True
                    break
                if current in visited:
                    continue
                visited.add(current)
                for neighbor in adj.get(current, set()):
                    if neighbor not in visited:
                        queue.append(neighbor)

            results.append({
                "from": s1["name"],
                "to": s2["name"],
                "reachable": found,
            })

    return results


def check_node_degrees(nodes, edges):
    """Calculate in-degree and out-degree for each node."""
    in_deg = defaultdict(int)
    out_deg = defaultdict(int)

    for edge in edges:
        out_deg[edge["source"]] += 1
        in_deg[edge["target"]] += 1

    stats = {
        "isolated": [],  # No edges at all
        "sink": [],  # Only incoming (dead ends)
        "source": [],  # Only outgoing (only accessible from here)
    }

    for node_id in nodes:
        i = in_deg.get(node_id, 0)
        o = out_deg.get(node_id, 0)

        if i == 0 and o == 0:
            stats["isolated"].append(node_id)
        elif o == 0 and i > 0:
            stats["sink"].append(node_id)
        elif i == 0 and o > 0:
            stats["source"].append(node_id)

    return in_deg, out_deg, stats


def check_edge_quality(edges):
    """Check edges for quality issues."""
    issues = []

    for edge in edges:
        if edge["distance"] <= 0:
            issues.append(f"Edge {edge['id']}: zero or negative distance ({edge['distance']}m)")

        if edge["type"] == "slope" and edge["elevationDelta"] > 0:
            issues.append(f"Slope {edge['id']} ({edge['name']}): goes uphill ({edge['elevationDelta']}m)")

        if edge["type"] == "lift" and edge["elevationDelta"] < 0:
            issues.append(f"Lift {edge['id']} ({edge['name']}): goes downhill ({edge['elevationDelta']}m)")

        if abs(edge["elevationDelta"]) > 2000:
            issues.append(f"Edge {edge['id']}: extreme elevation delta ({edge['elevationDelta']}m)")

    return issues


def main():
    print("=" * 60)
    print("Validating routing graph")
    print("=" * 60)

    graph, stations = load_graph()
    nodes = graph["nodes"]
    edges = graph["edges"]
    metadata = graph.get("metadata", {})

    print(f"\n--- Graph Summary ---")
    print(f"  Nodes: {len(nodes)}")
    print(f"  Edges: {len(edges)}")
    print(f"  Slopes: {metadata.get('slopeCount', '?')}")
    print(f"  Lifts: {metadata.get('liftCount', '?')}")
    print(f"  Stations: {len(stations)}")

    # Elevation range
    elevations = [n["ele"] for n in nodes.values()]
    if elevations:
        print(f"  Elevation range: {min(elevations)}m - {max(elevations)}m")

    # Node degree analysis
    print(f"\n--- Node Degree Analysis ---")
    in_deg, out_deg, deg_stats = check_node_degrees(nodes, edges)

    print(f"  Isolated nodes (no edges): {len(deg_stats['isolated'])}")
    print(f"  Sink nodes (only incoming): {len(deg_stats['sink'])}")
    print(f"  Source nodes (only outgoing): {len(deg_stats['source'])}")

    if deg_stats["sink"]:
        for n in deg_stats["sink"][:5]:
            station = nodes[n].get("station", "")
            print(f"    Sink: {n} ({nodes[n]['ele']}m){' - ' + station if station else ''}")

    if deg_stats["source"]:
        for n in deg_stats["source"][:5]:
            station = nodes[n].get("station", "")
            print(f"    Source: {n} ({nodes[n]['ele']}m){' - ' + station if station else ''}")

    # Edge quality
    print(f"\n--- Edge Quality ---")
    issues = check_edge_quality(edges)
    if issues:
        print(f"  Found {len(issues)} issues:")
        for issue in issues[:10]:
            print(f"    {issue}")
        if len(issues) > 10:
            print(f"    ... and {len(issues) - 10} more")
    else:
        print("  No quality issues found")

    # Difficulty distribution
    print(f"\n--- Slope Difficulty Distribution ---")
    diff_counts = defaultdict(int)
    for edge in edges:
        if edge["type"] == "slope":
            diff_counts[edge["difficulty"]] += 1
    for color in ["green", "blue", "red", "black"]:
        print(f"  {color}: {diff_counts.get(color, 0)}")

    # Lift type distribution
    print(f"\n--- Lift Type Distribution ---")
    lift_counts = defaultdict(int)
    for edge in edges:
        if edge["type"] == "lift":
            lift_counts[edge.get("liftType", "unknown")] += 1
    for lt, count in sorted(lift_counts.items()):
        print(f"  {lt}: {count}")

    # Station reachability
    print(f"\n--- Station Reachability (directed) ---")
    reachability = check_directed_reachability(nodes, edges, stations)
    unreachable = [r for r in reachability if not r["reachable"]]

    if unreachable:
        print(f"  UNREACHABLE pairs: {len(unreachable)}")
        for r in unreachable[:10]:
            print(f"    {r['from']} -> {r['to']}")
        if len(unreachable) > 10:
            print(f"    ... and {len(unreachable) - 10} more")
    else:
        print(f"  All {len(reachability)} station pairs are reachable!")

    # Named edges
    print(f"\n--- Named Elements ---")
    named_slopes = sum(1 for e in edges if e["type"] == "slope" and e["name"])
    named_lifts = sum(1 for e in edges if e["type"] == "lift" and e["name"])
    unnamed_slopes = sum(1 for e in edges if e["type"] == "slope" and not e["name"])
    unnamed_lifts = sum(1 for e in edges if e["type"] == "lift" and not e["name"])
    print(f"  Named slopes: {named_slopes}, Unnamed: {unnamed_slopes}")
    print(f"  Named lifts: {named_lifts}, Unnamed: {unnamed_lifts}")

    # Overall verdict
    print(f"\n{'=' * 60}")
    has_issues = bool(unreachable) or bool(deg_stats["isolated"]) or bool(issues)
    if has_issues:
        print("VALIDATION: WARNINGS FOUND (see above)")
    else:
        print("VALIDATION: PASSED")
    print("=" * 60)


if __name__ == "__main__":
    main()
