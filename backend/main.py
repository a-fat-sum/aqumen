from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from supabase import create_client, Client
from pydantic import BaseModel
import os
from dotenv import load_dotenv

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
def generate_report(location: LocationRequest):
    # This is a placeholder for the actual spatial queries we will do later
    return {
        "status": "success",
        "coordinates": {"lat": location.lat, "lng": location.lng},
        "message": "Report generation endpoint hit successfully."
    }
