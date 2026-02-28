"""
parse_gtfs.py — One-time script to generate a static GeoJSON from Sound Transit GTFS data.
Output: frontend/public/link_light_rail.geojson

Run: python parse_gtfs.py
"""
import os
import io
import csv
import json
import zipfile
import requests

GTFS_URL = "https://gtfs.sound.obaweb.org/prod/40_gtfs.zip"
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "../frontend/public/link_light_rail.geojson")

# Official Sound Transit Link Light Rail route IDs (1 Line, 2 Line, future lines)
# route_type=1 is subway/metro (light rail), route_type=0 is tram
LINK_ROUTE_TYPES = {"1", "0"}

def download_gtfs():
    print(f"Downloading GTFS from {GTFS_URL}...")
    r = requests.get(GTFS_URL, timeout=60)
    r.raise_for_status()
    print("✅ GTFS downloaded.")
    return zipfile.ZipFile(io.BytesIO(r.content))

def parse_routes(zf):
    """Return dict of route_id -> route info for light rail routes only."""
    routes = {}
    with zf.open("routes.txt") as f:
        reader = csv.DictReader(io.TextIOWrapper(f, encoding="utf-8-sig"))
        for row in reader:
            if row.get("route_type") in LINK_ROUTE_TYPES:
                routes[row["route_id"]] = {
                    "route_id": row["route_id"],
                    "route_short_name": row.get("route_short_name", ""),
                    "route_long_name": row.get("route_long_name", "Link Light Rail"),
                    "route_color": "#" + row.get("route_color", "00A550"),
                    "route_text_color": "#" + row.get("route_text_color", "FFFFFF"),
                }
    print(f"Found {len(routes)} light rail routes: {[r['route_short_name'] for r in routes.values()]}")
    return routes

def parse_trips(zf, route_ids):
    """Return dict of trip_id -> shape_id for our routes."""
    trip_to_shape = {}
    trip_to_route = {}
    with zf.open("trips.txt") as f:
        reader = csv.DictReader(io.TextIOWrapper(f, encoding="utf-8-sig"))
        for row in reader:
            if row["route_id"] in route_ids:
                # Only keep one trip per shape (to avoid duplicates)
                if row["shape_id"] not in trip_to_shape.values():
                    trip_to_shape[row["trip_id"]] = row["shape_id"]
                    trip_to_route[row["shape_id"]] = row["route_id"]
    return trip_to_shape, trip_to_route

def parse_shapes(zf, needed_shape_ids):
    """Return dict of shape_id -> list of [lng, lat] coordinates."""
    shapes = {}
    with zf.open("shapes.txt") as f:
        reader = csv.DictReader(io.TextIOWrapper(f, encoding="utf-8-sig"))
        for row in reader:
            sid = row["shape_id"]
            if sid not in needed_shape_ids:
                continue
            coord = [float(row["shape_pt_lon"]), float(row["shape_pt_lat"])]
            seq = int(row["shape_pt_sequence"])
            if sid not in shapes:
                shapes[sid] = []
            shapes[sid].append((seq, coord))
    # Sort by sequence
    for sid in shapes:
        shapes[sid].sort(key=lambda x: x[0])
        shapes[sid] = [c for _, c in shapes[sid]]
    return shapes

def parse_stops(zf, routes, trip_to_shape, trip_to_route):
    """Return list of stop features (GeoJSON points) enriched with route info."""
    # Build trip_id -> route_id mapping
    trip_to_route_id: dict = {}
    with zf.open("trips.txt") as f:
        reader = csv.DictReader(io.TextIOWrapper(f, encoding="utf-8-sig"))
        for row in reader:
            if row["route_id"] in routes:
                trip_to_route_id[row["trip_id"]] = row["route_id"]

    # Build stop_id -> set of route_ids from stop_times
    stop_to_routes: dict = {}
    with zf.open("stop_times.txt") as f:
        reader = csv.DictReader(io.TextIOWrapper(f, encoding="utf-8-sig"))
        for row in reader:
            route_id = trip_to_route_id.get(row["trip_id"])
            if route_id:
                stop_to_routes.setdefault(row["stop_id"], set()).add(route_id)

    relevant_stop_ids = set(stop_to_routes.keys())

    # Parse stop details and enrich with route info
    stop_features = []
    seen = set()
    with zf.open("stops.txt") as f:
        reader = csv.DictReader(io.TextIOWrapper(f, encoding="utf-8-sig"))
        for row in reader:
            sid = row["stop_id"]
            if sid in relevant_stop_ids and sid not in seen:
                seen.add(sid)
                route_ids_for_stop = list(stop_to_routes.get(sid, []))
                route_colors = list({routes[rid]["route_color"] for rid in route_ids_for_stop if rid in routes})
                route_short_names = list({routes[rid]["route_short_name"] for rid in route_ids_for_stop if rid in routes})
                route_long_names = list({routes[rid]["route_long_name"] for rid in route_ids_for_stop if rid in routes})

                # Primary color = first route's color (for pin styling)
                primary_color = route_colors[0] if route_colors else "#00A550"

                stop_features.append({
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "coordinates": [float(row["stop_lon"]), float(row["stop_lat"])]
                    },
                    "properties": {
                        "stop_id": sid,
                        "stop_name": row["stop_name"],
                        "feature_type": "station",
                        "route_color": primary_color,
                        "route_colors": route_colors,
                        "route_short_names": route_short_names,
                        "route_long_names": route_long_names,
                    }
                })
    print(f"Found {len(stop_features)} unique station stops.")
    return stop_features


def build_geojson(routes, shapes, trip_to_route, stop_features):
    features = []
    seen_shapes = set()

    for shape_id, coords in shapes.items():
        if shape_id in seen_shapes:
            continue
        seen_shapes.add(shape_id)
        route_id = trip_to_route.get(shape_id)
        route_info = routes.get(route_id, {})
        features.append({
            "type": "Feature",
            "geometry": {
                "type": "LineString",
                "coordinates": coords
            },
            "properties": {
                "shape_id": shape_id,
                "route_id": route_id,
                "route_short_name": route_info.get("route_short_name", "Link"),
                "route_long_name": route_info.get("route_long_name", "Link Light Rail"),
                "route_color": route_info.get("route_color", "#00A550"),
                "route_text_color": route_info.get("route_text_color", "#FFFFFF"),
                "feature_type": "route"
            }
        })

    features.extend(stop_features)
    return {"type": "FeatureCollection", "features": features}

def main():
    zf = download_gtfs()
    routes = parse_routes(zf)

    if not routes:
        print("❌ No light rail routes found! Check LINK_ROUTE_TYPES filter.")
        return

    trip_to_shape, trip_to_route = parse_trips(zf, set(routes.keys()))
    needed_shapes = set(trip_to_shape.values())
    print(f"Processing {len(needed_shapes)} unique route shapes...")

    shapes = parse_shapes(zf, needed_shapes)
    stop_features = parse_stops(zf, routes, trip_to_shape, trip_to_route)

    geojson = build_geojson(routes, shapes, trip_to_route, stop_features)

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(geojson, f)

    route_count = len([ft for ft in geojson["features"] if ft["properties"].get("feature_type") == "route"])
    station_count = len([ft for ft in geojson["features"] if ft["properties"].get("feature_type") == "station"])
    print(f"\n✅ GeoJSON written to {OUTPUT_PATH}")
    print(f"   {route_count} route line segments, {station_count} stations")

if __name__ == "__main__":
    main()
