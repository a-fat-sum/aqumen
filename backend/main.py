from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from supabase import create_client, Client
from pydantic import BaseModel
import os
import asyncio
from dotenv import load_dotenv
from services import get_yelp_data, get_osm_data, get_census_data

load_dotenv()

app = FastAPI()

# Allow frontend to call backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, set this specifically to the Vercel URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_SERVICE_KEY")
supabase: Client = create_client(url, key)

class LocationRequest(BaseModel):
    lat: float
    lng: float
    radius: int = 1500

@app.get("/")
def read_root():
    return {"message": "Aqumen API is running!"}

@app.post("/api/report")
async def generate_report(location: LocationRequest):
    # Concurrently fetch Yelp POIs, OSM structural data, and Census demographics
    yelp_task = get_yelp_data(location.lat, location.lng, radius=location.radius)
    osm_task = get_osm_data(location.lat, location.lng, radius=location.radius)
    census_task = get_census_data(location.lat, location.lng)
    
    yelp_response, osm_response, census_response = await asyncio.gather(yelp_task, osm_task, census_task)
    
    # Simple metric aggregation for Yelp/OSM
    yelp_businesses = yelp_response.get("businesses", []) if isinstance(yelp_response, dict) else []
    total_businesses = len(yelp_businesses)
    avg_rating = sum(b.get("rating", 0.0) for b in yelp_businesses) / total_businesses if total_businesses > 0 else 0.0
    
    osm_elements = osm_response.get("elements", []) if isinstance(osm_response, dict) else []
    total_osm_features = len(osm_elements)

    # Process Census Metrics
    population = "N/A"
    median_income = "N/A"
    tract_name = "N/A"
    if isinstance(census_response, dict) and "error" not in census_response:
        # Expected keys: NAME, B01003_001E, B19013_001E, state, county, tract
        
        # Clean Population
        raw_pop = census_response.get("B01003_001E")
        if raw_pop is not None:
            try:
                pop_val = int(raw_pop)
                population = pop_val if pop_val >= 0 else "N/A"
            except ValueError:
                pass
                
        # Clean Income
        raw_inc = census_response.get("B19013_001E")
        if raw_inc is not None:
            try:
                inc_val = int(raw_inc)
                median_income = inc_val if inc_val >= 0 else "N/A"
            except ValueError:
                pass
        
        # Clean up the tract name (e.g., "Census Tract 81.02, King County, Washington" -> "Tract 81.02")
        raw_name = census_response.get("NAME", "N/A")
        if "Census Tract " in raw_name:
            # slice out "Census " and get the segment before the first comma or semicolon
            tract_part = raw_name.split(";")[0].split(",")[0]
            tract_name = tract_part.replace("Census ", "")

    return {
        "status": "success",
        "coordinates": {"lat": location.lat, "lng": location.lng},
        "metrics": {
            "total_businesses_nearby": total_businesses,
            "average_business_rating": round(avg_rating, 2),
            "nearby_transit_and_parks": total_osm_features,
            "census_population": population,
            "census_median_income": median_income,
            "census_tract_name": tract_name
        },
        "raw_data": {
            "yelp": yelp_businesses,
            "osm": osm_elements,
            "census": census_response
        },
        "message": "Successfully analyzed the micro-locality."
    }
