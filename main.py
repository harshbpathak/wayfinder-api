import json
import math
import os
import re
from pathlib import Path
from typing import Optional

import httpx
from fastapi import FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from rapidfuzz import fuzz, process

API_KEY = os.environ.get("LOCATE_API_KEY")
DATA_PATH = Path(__file__).parent / "locations.json"
CONFIDENCE_THRESHOLD = 60
CANDIDATE_THRESHOLD = 65
OSRM_URL = os.environ.get("OSRM_URL", "https://router.project-osrm.org")
OSRM_PROFILE = os.environ.get("OSRM_PROFILE", "driving")
OSM_USER_AGENT = os.environ.get("OSM_USER_AGENT", "NITH-Wayfinder/1.0")
DEFAULT_ORIGIN = (31.7017559, 76.5228147)  # Gate 1, NIT Hamirpur, from OSM

app = FastAPI(title="NITH Wayfinder Locate API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"]
)

FRONTEND_PATH = Path(__file__).parent / "static" / "index.html"
STATIC_DIR = Path(__file__).parent / "static"
ASSETS_DIR = STATIC_DIR / "assets"
app.mount("/assets", StaticFiles(directory=ASSETS_DIR, check_dir=False), name="assets")

with DATA_PATH.open("r", encoding="utf-8") as locations_file:
    LOCATIONS = json.load(locations_file)

# Build search index from names and aliases
SEARCH_INDEX = []
for location_index, location in enumerate(LOCATIONS):
    SEARCH_INDEX.append((location["name"], location_index))
    SEARCH_INDEX.extend((alias, location_index) for alias in location.get("aliases", []))
SEARCH_TERMS = [term.lower() for term, _ in SEARCH_INDEX]

# Build a landmark lookup table for resolving named origins
ORIGIN_LANDMARKS = {}
for loc in LOCATIONS:
    if loc.get("latitude") is not None and loc.get("longitude") is not None:
        key = loc["name"].lower()
        coords = (loc["latitude"], loc["longitude"])
        ORIGIN_LANDMARKS[key] = coords
        ORIGIN_LANDMARKS[loc["id"]] = coords
        for alias in loc.get("aliases", []):
            ORIGIN_LANDMARKS[alias.lower()] = coords


def normalize_query(query: str) -> str:
    """Remove common spoken request framing before matching the place name."""
    normalized = query.lower().strip()
    # English patterns
    normalized = re.sub(
        r"^(?:where is|where's|how do i get to|how can i get to|take me to|find|locate|navigate to|go to|directions to|route to|show me)\s+",
        "",
        normalized,
    )
    # Hindi/Hinglish patterns
    normalized = re.sub(
        r"^(?:kahan hai|kidhar hai|kahan milega|kaise jaun|kaise pahunche|mujhe le chalo)\s+",
        "",
        normalized,
    )
    normalized = re.sub(r"^the\s+", "", normalized)
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized


def resolve_origin(origin: Optional[str], origin_lat: float, origin_lon: float) -> tuple:
    """Resolve a named origin landmark to coordinates, or use the provided lat/lon."""
    if origin:
        origin_clean = origin.lower().strip()
        # Try exact match first
        if origin_clean in ORIGIN_LANDMARKS:
            return ORIGIN_LANDMARKS[origin_clean]
        # Try fuzzy match
        landmark_names = list(ORIGIN_LANDMARKS.keys())
        matches = process.extractOne(origin_clean, landmark_names, scorer=fuzz.WRatio)
        if matches and matches[1] >= 70:
            return ORIGIN_LANDMARKS[matches[0]]
    return (origin_lat, origin_lon)


def check_api_key(x_api_key: Optional[str]) -> None:
    if API_KEY and x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


def osm_directions(location: dict, origin_lat: float, origin_lon: float) -> Optional[dict]:
    """Return a short route summary and GeoJSON geometry from OSRM."""
    if location.get("latitude") is None or location.get("longitude") is None:
        return None
    route_url = (
        f"{OSRM_URL.rstrip('/')}/route/v1/{OSRM_PROFILE}/"
        f"{origin_lon},{origin_lat};{location['longitude']},{location['latitude']}"
    )
    try:
        response = httpx.get(
            route_url,
            params={"overview": "full", "geometries": "geojson", "steps": "false"},
            headers={"User-Agent": OSM_USER_AGENT},
            timeout=4.0,
        )
        response.raise_for_status()
        route = response.json().get("routes", [])[0]
        distance_m = round(route["distance"])
        minutes = max(1, round(route["duration"] / 60))
        bearing = (math.degrees(math.atan2(
            location["longitude"] - origin_lon,
            location["latitude"] - origin_lat,
        )) + 360) % 360
        compass = ["north", "north-east", "east", "south-east", "south", "south-west", "west", "north-west"][round(bearing / 45) % 8]
        if distance_m >= 1000:
            distance = f"{distance_m / 1000:.1f} kilometres"
        else:
            distance = f"{distance_m} metres"
        return {
            "summary": f"About {distance} to the {compass}, or approximately {minutes} minutes by route.",
            "distance_meters": distance_m,
            "distance_km": round(distance_m / 1000, 2),
            "duration_minutes": minutes,
            "compass_direction": compass,
            "geometry": route.get("geometry"),
        }
    except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError):
        return None


def location_response(location: dict, confidence: float, origin_lat: float, origin_lon: float):
    """Build the API response for a found location, always computing OSRM route."""
    route = osm_directions(location, origin_lat, origin_lon)
    directions = route["summary"] if route else location.get("directions")
    # Don't return the placeholder text
    if directions and directions.startswith("FILL ME IN"):
        directions = None
    return {
        "found": True,
        "name": location["name"],
        "directions": directions,
        "confidence": round(confidence, 1),
        "candidates": [],
        "maps_link": location.get("maps_link"),
        "directions_source": "OpenStreetMap/OSRM" if route else "needs_verified_directions",
        "route": route,
        "destination": {
            "latitude": location.get("latitude"),
            "longitude": location.get("longitude"),
        },
    }


@app.get("/locate")
def locate(
    query: str = Query(..., min_length=2),
    origin_lat: float = Query(DEFAULT_ORIGIN[0], description="Origin latitude; defaults to NIT Gate 1"),
    origin_lon: float = Query(DEFAULT_ORIGIN[1], description="Origin longitude; defaults to NIT Gate 1"),
    origin: Optional[str] = Query(None, description="Named origin landmark, e.g. 'kailash hostel' or 'gate 1'"),
    x_api_key: Optional[str] = Header(default=None),
):
    check_api_key(x_api_key)

    # Resolve named origin to coordinates
    resolved_lat, resolved_lon = resolve_origin(origin, origin_lat, origin_lon)

    normalized_query = normalize_query(query)
    exact_matches = [index for index, term in enumerate(SEARCH_TERMS) if term == normalized_query]
    if exact_matches:
        location = LOCATIONS[SEARCH_INDEX[exact_matches[0]][1]]
        return location_response(location, 100.0, resolved_lat, resolved_lon)

    matches = process.extract(normalized_query, SEARCH_TERMS, scorer=fuzz.WRatio, limit=5)

    best_by_location = {}
    for _, score, search_index in matches:
        location_index = SEARCH_INDEX[search_index][1]
        if location_index not in best_by_location or score > best_by_location[location_index]:
            best_by_location[location_index] = score

    ranked = sorted(best_by_location.items(), key=lambda item: item[1], reverse=True)
    if not ranked:
        return {"found": False, "name": None, "directions": None, "confidence": 0, "candidates": []}

    top_index, top_score = ranked[0]
    if top_score < CANDIDATE_THRESHOLD:
        return {
            "found": False,
            "name": None,
            "directions": None,
            "confidence": round(top_score, 1),
            "candidates": [],
        }
    clear_winner = len(ranked) == 1 or (top_score - ranked[1][1]) >= 15
    if top_score >= CONFIDENCE_THRESHOLD and clear_winner:
        location = LOCATIONS[top_index]
        return location_response(location, top_score, resolved_lat, resolved_lon)

    return {
        "found": False,
        "name": None,
        "directions": None,
        "confidence": round(top_score, 1),
        "candidates": [LOCATIONS[index]["name"] for index, _ in ranked[:3]],
    }


@app.get("/locations")
def list_locations(x_api_key: Optional[str] = Header(default=None)):
    """Return all available campus locations for autocomplete and suggestions."""
    check_api_key(x_api_key)
    return [
        {
            "id": loc["id"],
            "name": loc["name"],
            "aliases": loc.get("aliases", []),
            "latitude": loc.get("latitude"),
            "longitude": loc.get("longitude"),
        }
        for loc in LOCATIONS
    ]


@app.get("/health")
def health():
    return {"status": "ok", "locations_loaded": len(LOCATIONS)}


@app.get("/", include_in_schema=False)
def frontend():
    return FileResponse(FRONTEND_PATH)
