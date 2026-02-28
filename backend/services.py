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
