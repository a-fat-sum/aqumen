import os
import httpx
import logging
from dotenv import load_dotenv
load_dotenv()

from supabase import Client

logger = logging.getLogger(__name__)

YELP_API_KEY = os.getenv("YELP_API_KEY")

async def get_yelp_data(lat: float, lng: float, radius: int = 1500):
    if not YELP_API_KEY:
        logger.warning("YELP_API_KEY is not set.")
        return {"error": "YELP_API_KEY missing"}

    url = "https://api.yelp.com/v3/businesses/search"
    headers = {
        "Authorization": f"Bearer {YELP_API_KEY}",
        "accept": "application/json"
    }
    params = {
        "latitude": lat,
        "longitude": lng,
        "radius": radius,
        "categories": "restaurants,cafes,coffee,gyms,active,shopping",
        "limit": 50,
        "sort_by": "distance"
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers, params=params, timeout=10.0)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Yelp API error: {str(e)}")
            return {"error": f"Yelp API request failed: {str(e)}"}

async def get_osm_data(lat: float, lng: float, radius: int = 1500):
    url = "http://overpass-api.de/api/interpreter"
    
    # Query for transit stops, parks, schools
    query = f"""
    [out:json][timeout:25];
    (
      node["highway"="bus_stop"](around:{radius},{lat},{lng});
      node["railway"="station"](around:{radius},{lat},{lng});
      way["leisure"="park"](around:{radius},{lat},{lng});
      way["amenity"="school"](around:{radius},{lat},{lng});
    );
    out center;
    """
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, data={"data": query}, timeout=15.0)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"OSM API error: {str(e)}")
            return {"error": f"OSM API request failed: {str(e)}"}

async def get_census_data(lat: float, lng: float):
    # 1. Convert Lat/Lng to Census FIPS via FCC API
    fcc_url = f"https://geo.fcc.gov/api/census/block/find?latitude={lat}&longitude={lng}&format=json"
    
    async with httpx.AsyncClient(follow_redirects=True) as client:
        try:
            res = await client.get(fcc_url, timeout=10.0)
            res.raise_for_status()
            data = res.json()
            
            state_fips = data.get("State", {}).get("FIPS")
            county_fips = data.get("County", {}).get("FIPS")
            
            if county_fips and len(county_fips) == 5:
                county_fips = county_fips[2:]
                
            block_fips = data.get("Block", {}).get("FIPS")
            tract_fips = block_fips[5:11] if block_fips else None
            
            if not (state_fips and county_fips and tract_fips):
                return {"error": "Could not map coordinates to Census tract"}
            
            # 2. Get Demographics from US Census (ACS 2022 5-year)
            # B01003_001E: Total Population, B19013_001E: Median Household Income
            census_url = f"https://api.census.gov/data/2022/acs/acs5?get=NAME,B01003_001E,B19013_001E&for=tract:{tract_fips}&in=state:{state_fips}+county:{county_fips}"
            res2 = await client.get(census_url, timeout=10.0)
            res2.raise_for_status()
            
            census_json = res2.json()
            if isinstance(census_json, list) and len(census_json) > 1:
                keys = census_json[0]
                values = census_json[1]
                return dict(zip(keys, values))
            else:
                return {"error": "Empty or malformed Census response"}
                
        except httpx.HTTPError as e:
            logger.error(f"Census/FCC API error: {str(e)}")
            return {"error": f"API request failed: {str(e)}"}

async def get_census_from_postgis(lat: float, lng: float, supabase_client: Client):
    """
    Fast PostGIS spatial lookup: finds which census tract polygon contains
    the given point and returns cached demographic data.
    Falls back to None if not found (caller should use live API as fallback).
    """
    try:
        # Call the Supabase RPC which runs:
        # SELECT name, population, median_income FROM census_tracts
        # WHERE ST_Contains(geom, ST_SetSRID(ST_MakePoint(lng, lat), 4326))
        res = supabase_client.rpc("get_tract_for_point", {
            "p_lat": lat,
            "p_lng": lng
        }).execute()

        if res.data and len(res.data) > 0:
            row = res.data[0]
            return {
                "name": row.get("name"),
                "population": row.get("population"),
                "median_income": row.get("median_income"),
                "geoid": row.get("geoid"),
                "source": "postgis"
            }
        else:
            logger.info("PostGIS census lookup: no tract found for point, will fall back to live API.")
            return None

    except Exception as e:
        logger.error(f"PostGIS census lookup error: {str(e)}")
        return None


FOURSQUARE_API_KEY = os.getenv("FOURSQUARE_API_KEY")

async def get_crime_data(lat: float, lng: float, radius: int = 1500):
    """
    Fetch recent crime incidents from Seattle Open Data Portal (Socrata API).
    Returns incident counts by category within the radius.
    No API key required.
    """
    # Socrata SoQL: filter by geo circle and last 12 months
    # Dataset: Seattle Police Department Incident Reports 2008-Present
    url = "https://data.seattle.gov/resource/tazs-3rd5.json"
    from datetime import datetime, timedelta
    one_year_ago = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%dT00:00:00")

    params = {
        "$where": f"within_circle(longitude,{lng},{lat},{radius}) AND offense_start_datetime >= '{one_year_ago}'",
        "$limit": 1000,
        "$select": "report_number,offense_parent_group,offense_start_datetime,longitude,latitude"
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, params=params, timeout=15.0)
            response.raise_for_status()
            data = response.json()

            # Aggregate by category
            categories: dict = {}
            incidents = []
            for item in data:
                cat = item.get("offense_parent_group", "Other")
                categories[cat] = categories.get(cat, 0) + 1
                if item.get("longitude") and item.get("latitude"):
                    incidents.append({
                        "lat": float(item["latitude"]),
                        "lng": float(item["longitude"]),
                        "category": cat,
                        "date": item.get("offense_start_datetime", "")[:10]
                    })

            # Sort categories by count
            top_categories = sorted(categories.items(), key=lambda x: x[1], reverse=True)

            return {
                "total_incidents": len(data),
                "categories": [{"name": k, "count": v} for k, v in top_categories[:5]],
                "incidents": incidents[:200]  # Cap for response size
            }
        except httpx.HTTPError as e:
            logger.error(f"Seattle Crime API error: {str(e)}")
            return {"error": f"Crime data request failed: {str(e)}"}

async def get_foursquare_pois(lat: float, lng: float, radius: int = 1500):
    """Fetch Places from Foursquare Places API (v3)."""
    if not FOURSQUARE_API_KEY:
        logger.warning("FOURSQUARE_API_KEY not set.")
        return {"error": "Foursquare API key not configured"}

    url = "https://api.foursquare.com/v3/places/search"
    headers = {
        "Authorization": FOURSQUARE_API_KEY,
        "accept": "application/json"
    }
    params = {
        "ll": f"{lat},{lng}",
        "radius": radius,
        "limit": 50,
        "sort": "DISTANCE",
        # Broad top-level category IDs: food, shops, arts, fitness, travel
        "categories": "13000,17000,10000,18000,19000"
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers, params=params, timeout=10.0)
            response.raise_for_status()
            data = response.json()
            places = data.get("results", [])
            return {
                "total": len(places),
                "places": [{
                    "fsq_id": p.get("fsq_id"),
                    "name": p.get("name"),
                    "categories": [c.get("name") for c in p.get("categories", [])],
                    "distance": p.get("distance"),
                    "lat": p.get("geocodes", {}).get("main", {}).get("latitude"),
                    "lng": p.get("geocodes", {}).get("main", {}).get("longitude"),
                    "rating": p.get("rating"),
                } for p in places]
            }
        except httpx.HTTPError as e:
            logger.error(f"Foursquare API error: {str(e)}")
            return {"error": f"Foursquare request failed: {str(e)}"}

import json as json_lib
import google.generativeai as genai

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

async def get_competitive_analysis(
    query: str,
    lat: float,
    lng: float,
    radius: int,
    pois: list,
    demographics: dict,
    crime: dict,
    walkability_score: int
) -> dict:
    """
    Use Gemini to perform a competitive & complementary business analysis
    for the proposed business at the given location.
    """
    if not GEMINI_API_KEY:
        return {"error": "GEMINI_API_KEY not configured"}

    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel("gemini-1.5-flash")

    # Build a concise POI summary for the prompt (avoid exceeding context)
    poi_lines = []
    for p in pois[:60]:  # Cap at 60 POIs to stay within token budget
        cats = ", ".join([
            (c.get("title") or c.get("alias") or c) if isinstance(c, dict) else str(c)
            for c in (p.get("categories") or [])
        ])
        dist = p.get("distance", "?")
        rating = p.get("rating", "N/A")
        poi_lines.append(f"- {p.get('name', 'Unknown')} ({cats}) — {dist}m away, rating: {rating}")
    pois_text = "\n".join(poi_lines) if poi_lines else "No POIs found in radius."

    pop = demographics.get("census_population", "unknown")
    income = demographics.get("census_median_income", "unknown")
    tract = demographics.get("census_tract_name", "")
    crime_total = crime.get("total_incidents", 0) if crime else 0
    top_crimes = ", ".join([c["name"] for c in (crime.get("categories") or [])[:3]]) if crime else "N/A"

    prompt = f"""You are an expert business location analyst. A user is evaluating opening:

**"{query}"**

Location: ({lat:.4f}, {lng:.4f}), analyzing a {radius}m radius.

## Area Context
- Census Tract: {tract}
- Population: {pop}
- Median Household Income: ${income:,} (if numeric)
- Aqumen Walkability Index: {walkability_score}/100
- Crime incidents (12 months): {crime_total} | Top categories: {top_crimes}

## Nearby POIs in Radius
{pois_text}

## Instructions
Analyze this location for the proposed business. Respond ONLY with a valid JSON object matching this exact schema:

{{
  "opportunity_score": <integer 0-100>,
  "opportunity_label": <"Excellent" | "Strong" | "Moderate" | "Challenging" | "Poor">,
  "competitors": [
    {{"name": "...", "distance_m": <int>, "threat_level": "high|medium|low", "reason": "..."}}
  ],
  "complementary": [
    {{"name": "...", "distance_m": <int>, "synergy_level": "high|medium|low", "reason": "..."}}
  ],
  "market_gaps": ["...", "..."],
  "demographic_assessment": "...",
  "summary": "3-4 sentence overall assessment of this location for the proposed business."
}}

Only reference businesses that appear in the POI list above. Be specific and opinionated."""

    try:
        response = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: model.generate_content(
                prompt,
                generation_config=genai.GenerationConfig(
                    response_mime_type="application/json",
                    temperature=0.4,
                )
            )
        )
        result = json_lib.loads(response.text)
        return result
    except Exception as e:
        logger.error(f"Gemini analysis error: {str(e)}")
        return {"error": f"Analysis failed: {str(e)}"}
