from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from supabase import create_client, Client
from pydantic import BaseModel
import os
import asyncio
from dotenv import load_dotenv
from services import get_yelp_data, get_osm_data

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

@app.get("/")
def read_root():
    return {"message": "Aqumen API is running!"}

@app.post("/api/report")
async def generate_report(location: LocationRequest):
    # Concurrently fetch Yelp POIs and OSM structural data
    yelp_task = get_yelp_data(location.lat, location.lng, radius=1500)
    osm_task = get_osm_data(location.lat, location.lng, radius=1500)
    
    yelp_response, osm_response = await asyncio.gather(yelp_task, osm_task)
    
    # Simple metric aggregation
    yelp_businesses = yelp_response.get("businesses", []) if isinstance(yelp_response, dict) else []
    total_businesses = len(yelp_businesses)
    avg_rating = sum(b.get("rating", 0.0) for b in yelp_businesses) / total_businesses if total_businesses > 0 else 0.0
    
    osm_elements = osm_response.get("elements", []) if isinstance(osm_response, dict) else []
    total_osm_features = len(osm_elements)

    return {
        "status": "success",
        "coordinates": {"lat": location.lat, "lng": location.lng},
        "metrics": {
            "total_businesses_nearby": total_businesses,
            "average_business_rating": round(avg_rating, 2),
            "nearby_transit_and_parks": total_osm_features
        },
        "raw_data": {
            "yelp": yelp_businesses,
            "osm": osm_elements
        },
        "message": "Successfully analyzed the micro-locality."
    }
