import os
import sys
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(__file__), '../backend/.env'))

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("Error: SUPABASE_URL or SUPABASE_SERVICE_KEY is missing from .env")
    sys.exit(1)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def setup_database():
    print("Setting up PostGIS database schemas in Supabase...")
    
    # Enable PostGIS
    try:
        supabase.rpc("install_postgis", {}).execute()
        print("✅ PostGIS extension confirmed.")
    except Exception as e:
        print(f"Note: Could not run install_postgis RPC. You may need to enable PostGIS manually in the Supabase Dashboard (Database -> Extensions). Error: {e}")

    # Create the census_tracts table via RPC (since standard service role users can't execute raw DDL via REST)
    # The user must create these RPC functions in the SQL Editor in Supabase, but we can document the SQL here.
    
    sql_schema = """
    -- Run this in the Supabase SQL Editor:
    
    -- 1. Enable PostGIS
    CREATE EXTENSION IF NOT EXISTS postgis;
    
    -- 2. Create the demographic shapefile table
    CREATE TABLE IF NOT EXISTS census_tracts (
        id SERIAL PRIMARY KEY,
        geoid VARCHAR(20) UNIQUE NOT NULL,
        state_fips VARCHAR(2) NOT NULL,
        county_fips VARCHAR(3) NOT NULL,
        tract_fips VARCHAR(6) NOT NULL,
        name VARCHAR(100),
        population INTEGER,
        median_income NUMERIC,
        geom GEOMETRY(MultiPolygon, 4326) -- SRID 4326 is standard GPS lat/lng
    );
    
    -- 3. Create a spatial index for lightning-fast queries
    CREATE INDEX IF NOT EXISTS census_tracts_geom_idx
        ON census_tracts
        USING GIST (geom);
    """
    
    print("\n" + "="*50)
    print("DATABASE INSTRUCTIONS:")
    print("You must run the following SQL snippet in your Supabase SQL Editor to prepare the database for ingestion:")
    print("="*50)
    print(sql_schema)
    print("="*50)

if __name__ == "__main__":
    setup_database()
