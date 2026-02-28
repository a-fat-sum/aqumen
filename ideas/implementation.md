# Architecture & Hosting Strategy: Local Business Intelligence MVP

## Overview
Before writing any implementation code, we need to define the logical components of the system and how they will interact. As requested, the goal is to prototype this entirely on "forever free" or highly generous free tiers until value is proven.

## 1. System Components

### A. The Client (Frontend Web App)
*   **Role:** The interactive user interface. It needs to render a map, handle user interactions (dropping pins, inputting queries), and visualize the resulting data (charts, lists, map overlays).
*   **Key Needs:** Fast rendering of map tiles and GeoJSON data overlays.

### B. The API Layer (Backend Backend/Orchestrator)
*   **Role:** The middleman. It receives coordinates from the Client, sanitizes them, and orchestrates the data gathering. It will query our internal database for demographics and potentially proxy external APIs (like Yelp) for live POI data to avoid exposing API keys on the Client.
*   **Key Needs:** Ability to securely handle API keys, execute database queries, and shape JSON responses.

### C. The Spatial Database
*   **Role:** Storing geographic data (like Census block group boundaries) and performing spatial relationships. For example, given a point (lat/lng), the database must quickly answer: "Which Census block group polygon contains this point?" or "Which pre-calculated POIs are within 1 mile of this point?"
*   **Key Needs:** PostGIS extension for PostgreSQL. Standard SQL databases are very slow at complex spatial math without it.

### D. Data Ingestion & ETL Pipeline (Offline/Async)
*   **Role:** Scripts to fetch raw data (US Census, GTFS transit data, Walk Score) and transform it into queryable spatial geometries in our Database.
*   **Key Needs:** Scripting environment (Python/Pandas/GeoPandas is industry standard here) for data wrangling.

---

## 2. Proposed Free-Tier Hosting Stack

To achieve a $0/month run rate for the prototype, here is the recommended hosting architecture:

| Component | Proposed Service | Why & Free Tier Limitations |
| :--- | :--- | :--- |
| **Frontend & API Layer** | **Vercel** (using Next.js) | Next.js allows us to build both the React frontend and the backend API routes in a single repository. Vercel's free tier is massive (100GB bandwidth/mo, generous serverless function execution). |
| **Spatial Database** | **Supabase** or **Neon** | Both provide a fully managed PostgreSQL database with the **PostGIS** extension pre-installed. Supabase gives 500MB database space (plenty for Seattle MVP). Neon separates storage and compute for unique scaling. |
| **Mapping Provider** | **Mapbox GL JS** | 50,000 free map loads per month. Extremely performant for visualizing large spatial datasets (like heat maps or census blocks). |
| **Data Ingestion** | **Local Machine & GitHub Actions** | We can run the heavy data-fetching Python scripts locally. If we need them to update automatically (e.g., refreshing POIs monthly), we can run them on GitHub Actions (2,000 free minutes/mo). |
| **External APIs** | **Yelp Fusion / Census API** | Census is free. Yelp allows 500 API calls per day on their free tier (enough for MVP testing). |

## 3. Discussion Points

Does this logical separation make sense to you? A few architectural choices to discuss:

1.  **The Monorepo approach:** Are you comfortable using a framework like Next.js that bundles the Frontend (React) and the API Layer (Node.js/Serverless) together, hosted on Vercel? The alternative is separating them (e.g., React on Netlify + Python FastAPI on Render/Fly.io), which is cleaner separation but slightly more setup overhead.
2.  **Database choice:** Have you worked with PostgreSQL/PostGIS before? Supabase is generally the easiest standard Postgres to spin up for free right now with PostGIS enabled.
