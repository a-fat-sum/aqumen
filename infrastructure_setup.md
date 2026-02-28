# Infrastructure Setup Guide

We are building a decoupled architecture: a React frontend communicating with a Python (FastAPI) backend, using a PostGIS database. Here is how to set up the free infrastructure you will need.

## 1. Database: Supabase (PostgreSQL + PostGIS)
Supabase provides a generous free tier for a fully managed PostgreSQL database with the required PostGIS extension.

1.  Go to [supabase.com](https://supabase.com/) and create a free account (you can sign in with GitHub).
2.  Click **"New Project"**.
3.  Name it (e.g., `aqumen-db`), and generate a strong database password. **Save this password securely; you will need it later.**
4.  Choose a region close to Seattle (e.g., US West).
5.  Once the database is provisioned (takes a few minutes), go to **Settings > Database**.
6.  Look for the **Connection String (URI)**. It will look like this: `postgresql://postgres.[project-ref]:[password]@aws-0-us-west-1.pooler.supabase.com:6543/postgres`
7.  **Hold onto this connection string.**

## 2. API Backend: Render (FastAPI)
Render offers a great free tier for hosting Dockerized or native Python web services. *Note: Free tier services "spin down" after 15 minutes of inactivity, meaning the first request after an idle period might take 30-60 seconds.*

1.  Go to [render.com](https://render.com/) and create a free account (sign in with GitHub).
2.  Since our code will be on GitHub, make sure you push the `aqumen` repository we are building to your GitHub account.
3.  In Render, click **"New" > "Web Service"**.
4.  Connect your GitHub repository to Render.
5.  Configure the service:
    *   **Root Directory:** `backend` (This is critical since we have a monorepo).
    *   **Environment:** `Python 3`
    *   **Build Command:** `pip install -r requirements.txt`
    *   **Start Command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`
6.  Under **Environment Variables**, you will eventually add your Supabase Connection String here (e.g., `DATABASE_URL`).
7.  Deploy! Render will give you a public URL (e.g., `https://aqumen-api.onrender.com`). **Save this URL.**

## 3. Frontend Web App: Vercel (React / Vite)
Vercel is the industry standard for hosting React applications with an incredible free tier.

1.  Go to [vercel.com](https://vercel.com/) and create a free account (sign in with GitHub).
2.  Click **"Add New" > "Project"**.
3.  Import the same `aqumen` repository from GitHub.
4.  Configure the project:
    *   **Root Directory:** `frontend` (Click Edit and select the frontend folder).
    *   **Framework Preset:** Vite
5.  Under **Environment Variables**, you will eventually add the Render URL (e.g., `VITE_API_URL = https://aqumen-api.onrender.com`).
6.  Click Deploy. Vercel will give you a public URL (e.g., `https://aqumen-frontend.vercel.app`).

## 4. Mapping Provider: Mapbox
We need an API key to load the interactive maps on the frontend.

1.  Go to [mapbox.com](https://mapbox.com/) and create a free account.
2.  Go to your **Account Dashboard**.
3.  Look for the **"Default public token"**. It starts with `pk.eyJ...`.
4.  **Save this token.** It will go into the frontend environment variables later.

---

**Summary Checklist:** After completing these steps, you should have:
- [ ] A Supabase `DATABASE_URL` connection string.
- [ ] A Mapbox public token (`pk....`).
- [ ] A Render web service (linked to the `backend` folder).
- [ ] A Vercel deployment (linked to the `frontend` folder).
