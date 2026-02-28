import asyncio
from dotenv import load_dotenv
load_dotenv()
from services import get_yelp_data, get_osm_data

async def main():
    lat = 47.6062
    lng = -122.3321
    
    print("Testing Yelp API...")
    yelp = await get_yelp_data(lat, lng)
    if "error" in yelp:
        print("Yelp Error:", yelp["error"])
    else:
        businesses = yelp.get("businesses", [])
        print(f"Yelp returned {len(businesses)} businesses.")
        if businesses:
            print(f"First business: {businesses[0]['name']}")

    print("\nTesting OSM API...")
    osm = await get_osm_data(lat, lng)
    if "error" in osm:
        print("OSM Error:", osm["error"])
    else:
        elements = osm.get("elements", [])
        print(f"OSM returned {len(elements)} elements.")
        if elements:
            print(f"First OSM element tags: {elements[0].get('tags')}")

if __name__ == "__main__":
    asyncio.run(main())
