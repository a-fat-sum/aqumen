import os
import sys
import requests
import zipfile
import io
import geopandas as gpd
from shapely.geometry import mapping
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv(os.path.join(os.path.dirname(__file__), '../backend/.env'))

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("Error: SUPABASE_URL or SUPABASE_SERVICE_KEY is missing from .env")
    sys.exit(1)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Washington State FIPS is 53. King County (Seattle) is 033.
CENSUS_SHAPEFILE_URL = "https://www2.census.gov/geo/tiger/TIGER2022/TRACT/tl_2022_53_tract.zip"

def download_and_extract_shapefiles():
    print(f"Downloading Washington State Census Tracts from {CENSUS_SHAPEFILE_URL}...")
    response = requests.get(CENSUS_SHAPEFILE_URL)
    response.raise_for_status()
    
    # Extract
    with zipfile.ZipFile(io.BytesIO(response.content)) as z:
        z.extractall("tmp_shapefiles")
    
    print("✅ Download and extraction complete.")

def process_and_upload():
    print("Loading geographic shapes via GeoPandas...")
    # Read the shapefile
    gdf = gpd.read_file("tmp_shapefiles/tl_2022_53_tract.shp")
    
    # Standardize coordinate reference system to standard GPS Lat/Lng (WGS84 / SRID 4326)
    gdf = gdf.to_crs(epsg=4326)
    
    # Filter only for King County (FIPS 033) which contains Seattle/Bellevue to save DB space
    king_county = gdf[gdf['COUNTYFP'] == '033']
    
    print(f"Found {len(king_county)} tracts in King County. Preparing to upload to Supabase.")
    
    # Convert geometries to GeoJSON format for the Supabase RPC
    inserted = 0
    records = []
    
    for idx, row in king_county.iterrows():
        # Shapely geometry to GeoJSON
        geojson_geom = mapping(row.geometry)
        
        records.append({
            "geoid": row['GEOID'],
            "state_fips": row['STATEFP'],
            "county_fips": row['COUNTYFP'],
            "tract_fips": row['TRACTCE'],
            "name": row['NAME'],
            # Note: Population & Income are usually populated from a separate ACS API pull 
            # or we can write a script to backfill these later. For now, we seed the geometry.
            "population": None,
            "median_income": None,
            "geom": geojson_geom # We will need a specialized insert mechanism for PostGIS
        })

    print("Sample record prepared:")
    print(records[0]["geoid"], records[0]["name"])
    
    # Due to Supabase REST limitations with complex PostGIS multi-polygons, 
    # we typically need to run an RPC wrapper to decode GeoJSON -> PostGIS Geometry.
    print("\n⚠️ Note: Native Supabase client insert() doesn't automatically convert GeoJSON to PostGIS Geometries.")
    print("You'll need an RPC helper in Supabase to insert these cleanly. See implementation plan.")

if __name__ == "__main__":
    if not os.path.exists("tmp_shapefiles"):
        download_and_extract_shapefiles()
    
    process_and_upload()
