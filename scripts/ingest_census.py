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
    total_tracts = len(king_county)
    inserted = 0
    records = []
    
    for idx, row in king_county.iterrows():
        # Shapely geometry to GeoJSON
        geojson_geom = mapping(row.geometry)
        
        print(f"[{idx+1}/{total_tracts}] Uploading Tract {row['GEOID']} ({row['NAME']})")
        
        try:
            res = supabase.rpc("insert_census_tract", {
                "p_geoid": row['GEOID'],
                "p_state_fips": row['STATEFP'],
                "p_county_fips": row['COUNTYFP'],
                "p_tract_fips": row['TRACTCE'],
                "p_name": row['NAME'],
                "p_geojson": geojson_geom
            }).execute()
            inserted += 1
        except Exception as e:
            print(f"Failed to insert {row['GEOID']}: {e}")

    print(f"\n✅ Successfully inserted {inserted}/{total_tracts} Census Tracts into Supabase PostGIS.")

if __name__ == "__main__":
    if not os.path.exists("tmp_shapefiles"):
        download_and_extract_shapefiles()
    
    process_and_upload()
