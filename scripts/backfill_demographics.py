import os
import asyncio
import sys
from dotenv import load_dotenv
from supabase import create_client, Client

# We need the services module from the backend directory
sys.path.append(os.path.join(os.path.dirname(__file__), '../backend'))
from services import get_census_data

load_dotenv(os.path.join(os.path.dirname(__file__), '../backend/.env'))

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("Error: SUPABASE_URL or SUPABASE_SERVICE_KEY is missing from .env")
    sys.exit(1)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

async def backfill_demographics():
    """
    Fetches all census tracts that are missing population/income data from
    the Supabase database, then calls the live Census API to populate them.
    
    This is a one-time script to pre-warm the database so future lookups
    can be served entirely from PostGIS without any external API calls.
    """
    print("Fetching tracts with missing demographics from Supabase...")

    # Pull only tracts with NULL population (not yet backfilled)
    # We need the geoid + we need a centroid point to query Census API
    # The Supabase RPC get_tract_centroids returns (geoid, state_fips, county_fips, tract_fips, lat, lng)
    res = supabase.rpc("get_tract_centroids_for_backfill").execute()

    if not res.data:
        print("No tracts found to backfill. All tracts may already have demographics!")
        return

    tracts = res.data
    total = len(tracts)
    print(f"Found {total} tracts to backfill.\n")

    success = 0
    failed = 0

    for i, tract in enumerate(tracts):
        geoid = tract["geoid"]
        lat = tract["centroid_lat"]
        lng = tract["centroid_lng"]

        print(f"[{i+1}/{total}] Fetching demographics for GEOID {geoid} (centroid: {lat:.4f}, {lng:.4f})")

        census_data = await get_census_data(lat, lng)

        if isinstance(census_data, dict) and "error" not in census_data:
            raw_pop = census_data.get("B01003_001E")
            raw_inc = census_data.get("B19013_001E")

            try:
                population = int(raw_pop) if raw_pop and int(raw_pop) >= 0 else None
            except (ValueError, TypeError):
                population = None

            try:
                median_income = int(raw_inc) if raw_inc and int(raw_inc) >= 0 else None
            except (ValueError, TypeError):
                median_income = None

            # Update the existing row in Supabase
            update_res = supabase.table("census_tracts").update({
                "population": population,
                "median_income": median_income
            }).eq("geoid", geoid).execute()

            print(f"  ✅ Population: {population}, Median Income: {median_income}")
            success += 1
        else:
            print(f"  ⚠️  Census API failed or returned error: {census_data}")
            failed += 1

        # Small delay to be kind to the Census API rate limits
        await asyncio.sleep(0.5)

    print(f"\n{'='*50}")
    print(f"Backfill complete: {success}/{total} tracts updated, {failed} failed.")

if __name__ == "__main__":
    asyncio.run(backfill_demographics())
