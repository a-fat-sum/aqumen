# Brainstorming: Local Business Intelligence Web Service

## 1. The Core Idea
A web-based service providing micro-locality (block-level) intelligence for small business owners to help them choose the optimal physical location for their retail or service business. The service should be general enough for any type of business (not just Pilates studios).

## 2. Geographically Scoped MVP
*   **Initial Focus:** Greater Seattle Area (Seattle, Redmond, Bellevue, Sammamish, Issaquah).

## 3. The User Experience (UX) Flow
We are planning two distinct phases of UX tools.

### Phase 1: The "Report Card" (Pin Drop Strategy)
*   **Action:** The user drops a pin on a specific location they are considering (e.g., they found a lease listing).
*   **Output:** The system generates a comprehensive "Report Card" detailing demographics, proxy foot traffic, competitors, and complementary businesses within a specific radius of that pin.

### Phase 2: The "Discovery" (Heat Map Strategy)
*   **Action:** The user inputs their ideal business criteria (e.g., high income, few competitors, high foot traffic proxy).
*   **Output:** The system generates a map highlighting the best neighborhoods or target blocks that match those criteria in the Greater Seattle area.

## 4. Core Data Dimensions & Low-Cost Proxies
To keep MVP costs low/free, we will use proxy data heavily.
*   **Demographics:** 
    *   *Source:* US Census Bureau (American Community Survey - block group level) provides free, granular demographics via API.
*   **Business POIs (Competitors/Complements):** 
    *   *Source:* Yelp Fusion API (free tier) or OpenStreetMap (free) to map existing businesses. Google Places API (freemium/pay-as-you-go).
*   **Transit & Mobility:** 
    *   *Source:* Local city General Transit Feed Specification (GTFS) data (usually free - e.g., King County Metro/Sound Transit data).
*   **Foot Traffic (Proxies):** 
    *   *Source:* Instead of paying for live tracking, we will calculate a "walkability score" or "activity index" based on the density of:
        *   Nearby coffee shops/cafes.
        *   Proximity to major transit stops.
        *   Walk Score API (if free tier exists, or map our own).

## 5. Next Steps: Building the Technology Stack
*We need to define the technical architecture for the MVP (Phase 1).*
