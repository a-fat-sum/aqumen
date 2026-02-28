import os
import httpx
import logging

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
        "sort_by": "rating"
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
