import { useState, useRef, useMemo } from 'react';
import Map, { Marker, Source, Layer, ScaleControl } from 'react-map-gl';
import type { ViewStateChangeEvent, MapLayerMouseEvent, MapRef } from 'react-map-gl';
import 'mapbox-gl/dist/mapbox-gl.css';
import { MapPin, RefreshCcw, Coffee, Bus, Store, Utensils, TreePine, BookOpen, Dumbbell, Users, ChevronLeft, ChevronRight, SlidersHorizontal, Shield, Bike, Train } from 'lucide-react';
import * as turf from '@turf/turf';

const MAPBOX_TOKEN = import.meta.env.VITE_MAPBOX_TOKEN;

const DEFAULT_VIEW_STATE = {
  longitude: -122.3321, // Seattle Longitude
  latitude: 47.6062,    // Seattle Latitude
  zoom: 12,
  pitch: 0,
  bearing: 0
};

function App() {
  const [viewState, setViewState] = useState(DEFAULT_VIEW_STATE);

  const [pinData, setPinData] = useState<{ lat: number, lng: number } | null>(null);
  const [reportData, setReportData] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const mapRef = useRef<MapRef>(null);
  const [mapboxPois, setMapboxPois] = useState<any[]>([]);

  // New UI States
  const [radius, setRadius] = useState<number>(1500); // 1.5km default
  const [poiPage, setPoiPage] = useState<number>(0);
  const POIS_PER_PAGE = 5;

  const [showFilters, setShowFilters] = useState({
    commercial: true,
    transit: true,
    parks: true,
    civic: true,
    crime: false,
    lightRail: true,
    isochrone: false
  });
  const [isochrone, setIsochrone] = useState<any>(null);
  const [crimeData, setCrimeData] = useState<any>(null);
  const [foursquarePois, setFoursquarePois] = useState<any[]>([]);

  const handleMapClick = (evt: MapLayerMouseEvent) => {
    setPinData({
      lng: evt.lngLat.lng,
      lat: evt.lngLat.lat
    });
    setReportData(null);
    setMapboxPois([]);
    setIsochrone(null);
    setCrimeData(null);
    setFoursquarePois([]);
    setError(null);
    setPoiPage(0);
  };

  const handleResetMap = () => {
    setViewState(DEFAULT_VIEW_STATE);
    setPinData(null);
    setReportData(null);
    setMapboxPois([]);
    setIsochrone(null);
    setCrimeData(null);
    setFoursquarePois([]);
    setError(null);
    setRadius(1500);
    setPoiPage(0);
  };

  const generateReport = async () => {
    if (!pinData) return;

    setLoading(true);
    setError(null);

    // Initialize empty report data to accept streams
    setReportData({
      status: "success",
      metrics: {},
      raw_data: { yelp: [], osm: [], census: {} }
    });

    // 1. Instantly Extract native Mapbox POIs from the rendered map canvas
    if (mapRef.current) {
      try {
        const mapboxMap = mapRef.current.getMap();
        // Query all POI/icon/symbol layers rather than just poi-label
        const features = mapboxMap.queryRenderedFeatures();

        const uniqueMapboxPois = new globalThis.Map<string, any>();
        features.forEach(f => {
          // Native mapbox markers typically have a point geometry and name, or are in specific layers
          const isPoiLayer = f.layer?.id?.includes('poi') || f.layer?.id?.includes('label') || f.layer?.id?.includes('place');
          if (isPoiLayer && f.geometry.type === 'Point' && f.properties?.name) {
            // @ts-ignore Turf types with Mapbox GeoJSON
            const dist = turf.distance([pinData.lng, pinData.lat], f.geometry.coordinates, { units: 'meters' });
            if (dist <= radius) {
              if (!uniqueMapboxPois.has(f.properties.name)) {
                uniqueMapboxPois.set(f.properties.name, {
                  id: `mapbox-${uniqueMapboxPois.size}`,
                  name: f.properties.name,
                  categories: [{ title: f.properties.type || f.properties.class || 'Local Business' }],
                  rating: 'N/A',
                  distance: dist,
                  lng: f.geometry.coordinates[0],
                  lat: f.geometry.coordinates[1]
                });
              }
            }
          }
        });
        const parsedPois = Array.from(uniqueMapboxPois.values());
        setMapboxPois(parsedPois);
      } catch (e) {
        console.error("Mapbox POI extraction failed:", e);
      }
    }

    // 2. Fire Decomposed Backend + Isochrone Requests in parallel
    const headers = { 'Content-Type': 'application/json' };
    const body = JSON.stringify({ ...pinData, radius });
    const baseUrl = import.meta.env.VITE_API_URL;

    // Isochrone: 5, 10, 15 min walking contours (Mapbox API, no backend needed)
    const fetchIsochrone = fetch(
      `https://api.mapbox.com/isochrone/v1/mapbox/walking/${pinData.lng},${pinData.lat}?contours_minutes=5,10,15&contours_colors=ade8f4,0096c7,023e8a&polygons=true&access_token=${MAPBOX_TOKEN}`
    ).then(r => r.json()).then(data => {
      if (data?.features) setIsochrone(data);
    }).catch(e => console.error('Isochrone error:', e));

    const fetchYelp = fetch(`${baseUrl}/api/report/yelp`, { method: 'POST', headers, body })
      .then(res => res.json())
      .then(data => {
        setReportData((prev: any) => ({
          ...prev,
          metrics: { ...prev.metrics, ...data.metrics },
          raw_data: { ...prev.raw_data, yelp: data.raw_data.yelp }
        }));
      });

    const fetchOsm = fetch(`${baseUrl}/api/report/osm`, { method: 'POST', headers, body })
      .then(res => res.json())
      .then(data => {
        setReportData((prev: any) => ({
          ...prev,
          metrics: { ...prev.metrics, ...data.metrics },
          raw_data: { ...prev.raw_data, osm: data.raw_data.osm }
        }));
      });

    const fetchCensus = fetch(`${baseUrl}/api/report/census`, { method: 'POST', headers, body })
      .then(res => res.json())
      .then(data => {
        setReportData((prev: any) => ({
          ...prev,
          metrics: { ...prev.metrics, ...data.metrics },
          raw_data: { ...prev.raw_data, census: data.raw_data.census }
        }));
      });

    const fetchCrime = fetch(`${baseUrl}/api/report/crime`, { method: 'POST', headers, body })
      .then(res => res.json())
      .then(data => {
        if (data?.raw_data?.crime) setCrimeData(data.raw_data.crime);
      }).catch(e => console.error('Crime data error:', e));

    const fetchFoursquare = fetch(`${baseUrl}/api/report/foursquare`, { method: 'POST', headers, body })
      .then(res => res.json())
      .then(data => {
        if (data?.raw_data?.foursquare) setFoursquarePois(data.raw_data.foursquare);
      }).catch(e => console.error('Foursquare error:', e));

    try {
      await Promise.allSettled([fetchIsochrone, fetchYelp, fetchOsm, fetchCensus, fetchCrime, fetchFoursquare]);
    } catch (err: any) {
      setError("Some data sources failed to load.");
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  // Merge Yelp data with Mapbox Canvas POIs
  const mergedPois = useMemo(() => {
    if (!reportData) return [];

    const yelpBusinesses = reportData.raw_data?.yelp || [];
    const mergedDict = new globalThis.Map<string, any>();

    // Add Mapbox POIs first
    mapboxPois.forEach(p => mergedDict.set(p.name.toLowerCase(), p));

    // Add Foursquare POIs (enriches coverage)
    foursquarePois.forEach((p: any) => {
      if (p.name && p.lat && p.lng) {
        const key = p.name.toLowerCase();
        if (!mergedDict.has(key)) {
          mergedDict.set(key, {
            id: `fsq-${p.fsq_id}`,
            name: p.name,
            categories: (p.categories || []).map((c: string) => ({ title: c })),
            rating: p.rating || 'N/A',
            distance: p.distance,
            lng: p.lng,
            lat: p.lat
          });
        }
      }
    });

    // Override with Yelp POIs (since Yelp has detailed ratings)
    yelpBusinesses.forEach((bz: any) => {
      mergedDict.set(bz.name.toLowerCase(), {
        id: bz.id,
        name: bz.name,
        categories: bz.categories,
        rating: bz.rating,
        distance: bz.distance,
        lng: bz.coordinates?.longitude,
        lat: bz.coordinates?.latitude
      });
    });

    return Array.from(mergedDict.values()).sort((a, b) => a.distance - b.distance);
  }, [reportData, mapboxPois]);

  // Robust parsing to prevent NaN
  const parseMetric = (val: any, format: 'number' | 'currency' = 'number') => {
    if (val === undefined || val === null || val === "N/A" || val === "--") return "N/A";
    const num = Number(val);
    if (isNaN(num)) return "N/A";
    if (format === 'currency') return `$${num.toLocaleString()}`;
    return num.toLocaleString();
  };

  return (
    <div className="flex h-screen w-full font-sans bg-gray-50">
      {/* Sidebar / Report Card Area */}
      <div className="w-[450px] shrink-0 bg-white shadow-xl z-10 flex flex-col pt-8 border-r border-gray-200">
        <h1 className="text-2xl font-bold px-6 text-gray-800 tracking-tight">Aqumen</h1>
        <p className="text-sm text-gray-500 px-6 mt-2 pb-6 border-b border-gray-100">
          Drop a pin on the map to generate a micro-locality report card for any business.
        </p>

        <div className="flex-1 overflow-y-auto px-6 mt-6 pb-12">
          {pinData ? (
            <div className="bg-blue-50 border border-blue-100 rounded-lg p-5">
              <div className="flex justify-between items-start mb-4">
                <div>
                  <h3 className="font-semibold text-blue-900 mb-1">Location Selected</h3>
                  <p className="text-xs text-blue-700 font-mono">Lat: {pinData.lat.toFixed(4)}, Lng: {pinData.lng.toFixed(4)}</p>
                </div>
              </div>

              {/* Radius Configuration */}
              <div className="mb-5 bg-white p-3 rounded-md border border-blue-100/50 shadow-sm">
                <div className="flex justify-between items-center mb-2">
                  <label className="text-xs font-semibold text-gray-700 flex items-center gap-1">
                    <SlidersHorizontal className="w-3 h-3" />
                    Search Radius
                  </label>
                  <span className="text-xs font-bold text-blue-600">{radius} meters</span>
                </div>
                <input
                  type="range"
                  min="500"
                  max="3000"
                  step="100"
                  value={radius}
                  onChange={(e) => setRadius(parseInt(e.target.value))}
                  className="w-full h-1.5 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-blue-600"
                />
                <div className="flex justify-between text-[10px] text-gray-400 mt-1">
                  <span>500m</span>
                  <span>1.5km</span>
                  <span>3km</span>
                </div>
              </div>

              {/* Layer Filters */}
              {reportData && (
                <div className="mb-5 bg-white p-3 rounded-md border border-gray-100 shadow-sm">
                  <h5 className="text-xs font-semibold text-gray-700 mb-2">Map Layers</h5>
                  <div className="flex flex-wrap gap-2">
                    <button onClick={() => setShowFilters(f => ({ ...f, commercial: !f.commercial }))}
                      className={`px-3 py-1.5 rounded-full text-xs font-semibold flex items-center gap-1.5 transition-colors border ${showFilters.commercial ? 'bg-blue-100 text-blue-700 border-blue-200' : 'bg-white text-gray-500 border-gray-200'}`}>
                      <Store className="w-3 h-3" /> Commercial
                    </button>
                    <button onClick={() => setShowFilters(f => ({ ...f, transit: !f.transit }))}
                      className={`px-3 py-1.5 rounded-full text-xs font-semibold flex items-center gap-1.5 transition-colors border ${showFilters.transit ? 'bg-teal-100 text-teal-700 border-teal-200' : 'bg-white text-gray-500 border-gray-200'}`}>
                      <Bus className="w-3 h-3" /> Transit
                    </button>
                    <button onClick={() => setShowFilters(f => ({ ...f, parks: !f.parks }))}
                      className={`px-3 py-1.5 rounded-full text-xs font-semibold flex items-center gap-1.5 transition-colors border ${showFilters.parks ? 'bg-green-100 text-green-700 border-green-200' : 'bg-white text-gray-500 border-gray-200'}`}>
                      <TreePine className="w-3 h-3" /> Parks
                    </button>
                    <button onClick={() => setShowFilters(f => ({ ...f, civic: !f.civic }))}
                      className={`px-3 py-1.5 rounded-full text-xs font-semibold flex items-center gap-1.5 transition-colors border ${showFilters.civic ? 'bg-indigo-100 text-indigo-700 border-indigo-200' : 'bg-white text-gray-500 border-gray-200'}`}>
                      <BookOpen className="w-3 h-3" /> Civic
                    </button>
                    <button onClick={() => setShowFilters(f => ({ ...f, crime: !f.crime }))}
                      className={`px-3 py-1.5 rounded-full text-xs font-semibold flex items-center gap-1.5 transition-colors border ${showFilters.crime ? 'bg-red-100 text-red-600 border-red-200' : 'bg-white text-gray-500 border-gray-200'}`}>
                      <Shield className="w-3 h-3" /> Crime
                    </button>
                    <button onClick={() => setShowFilters(f => ({ ...f, isochrone: !f.isochrone }))}
                      className={`px-3 py-1.5 rounded-full text-xs font-semibold flex items-center gap-1.5 transition-colors border ${showFilters.isochrone ? 'bg-sky-100 text-sky-700 border-sky-200' : 'bg-white text-gray-500 border-gray-200'}`}>
                      <Bike className="w-3 h-3" /> Walkshed
                    </button>
                    <button onClick={() => setShowFilters(f => ({ ...f, lightRail: !f.lightRail }))}
                      className={`px-3 py-1.5 rounded-full text-xs font-semibold flex items-center gap-1.5 transition-colors border ${showFilters.lightRail ? 'bg-emerald-100 text-emerald-700 border-emerald-200' : 'bg-white text-gray-500 border-gray-200'}`}>
                      <Train className="w-3 h-3" /> Light Rail
                    </button>
                  </div>
                </div>
              )}

              <button
                onClick={generateReport}
                disabled={loading}
                className="mt-6 w-full bg-blue-600 hover:bg-blue-700 disabled:bg-blue-300 text-white font-medium py-2.5 px-4 rounded-md shadow-sm transition-colors flex justify-center items-center">
                {loading ? (
                  <span className="animate-pulse">Building Dynamic Report...</span>
                ) : "Generate Report"}
              </button>

              {error && (
                <div className="mt-4 p-3 bg-red-50 text-red-700 text-sm rounded border border-red-200">
                  {error}
                </div>
              )}

              {reportData && (
                <div className="mt-8">
                  <h4 className="font-bold text-gray-800 border-b pb-2 mb-4">Micro-Locality Analysis</h4>

                  <div className="space-y-4">
                    {/* Commercial Meta */}
                    <div className="p-4 bg-white border border-gray-100 rounded-lg shadow-sm">
                      <div className="flex items-center gap-3 mb-3">
                        <Store className="text-blue-500 w-5 h-5" />
                        <h5 className="font-semibold text-gray-800 text-sm">Commercial Engine</h5>
                      </div>
                      <div className="grid grid-cols-2 gap-3">
                        <div className="bg-blue-50/50 p-3 rounded-md border border-blue-100/50 relative">
                          {loading && reportData.metrics?.total_businesses_nearby === undefined && (
                            <div className="absolute inset-0 bg-blue-50/50 flex justify-center items-center rounded-md"><RefreshCcw className="w-4 h-4 animate-spin text-blue-400" /></div>
                          )}
                          <p className="text-[10px] text-blue-600 font-bold uppercase tracking-wider mb-1">Nearby POIs</p>
                          <p className="text-2xl font-black text-gray-800">{parseMetric(reportData.metrics?.total_businesses_nearby)}</p>
                        </div>
                        <div className="bg-orange-50/50 p-3 rounded-md border border-orange-100/50 relative">
                          {loading && reportData.metrics?.average_business_rating === undefined && (
                            <div className="absolute inset-0 bg-orange-50/50 flex justify-center items-center rounded-md"><RefreshCcw className="w-4 h-4 animate-spin text-orange-400" /></div>
                          )}
                          <p className="text-[10px] text-orange-600 font-bold uppercase tracking-wider mb-1">Avg Rating</p>
                          <p className="text-2xl font-black text-gray-800">{parseMetric(reportData.metrics?.average_business_rating)}</p>
                        </div>
                      </div>
                    </div>

                    {/* Structural Meta */}
                    <div className="p-4 bg-white border border-gray-100 rounded-lg shadow-sm">
                      <div className="flex items-center gap-3 mb-3">
                        <TreePine className="text-teal-500 w-5 h-5" />
                        <h5 className="font-semibold text-gray-800 text-sm">Civic & Transit Proxies</h5>
                      </div>
                      <div className="bg-teal-50/50 p-3 rounded-md border border-teal-100/50 relative">
                        {loading && reportData.metrics?.nearby_transit_and_parks === undefined && (
                          <div className="absolute inset-0 bg-teal-50/50 flex justify-center items-center rounded-md"><RefreshCcw className="w-4 h-4 animate-spin text-teal-400" /></div>
                        )}
                        <p className="text-[10px] text-teal-600 font-bold uppercase tracking-wider mb-1">Nodes (Transit, Parks, Schools)</p>
                        <p className="text-2xl font-black text-gray-800">{parseMetric(reportData.metrics?.nearby_transit_and_parks)}</p>
                      </div>
                    </div>

                    {/* Demographic Meta */}
                    <div className="p-4 bg-white border border-gray-100 rounded-lg shadow-sm">
                      <div className="flex items-center gap-3 mb-3">
                        <Users className="text-purple-500 w-5 h-5" />
                        <h5 className="font-semibold text-gray-800 text-sm">Local Demographics</h5>
                      </div>
                      <p className="text-xs text-gray-400 mb-3 ml-8">Based on ACS 2022 5-Year Data for {reportData.metrics?.census_tract_name || "Region"}</p>
                      <div className="grid grid-cols-2 gap-3">
                        <div className="bg-purple-50/50 p-3 rounded-md border border-purple-100/50 relative">
                          {loading && reportData.metrics?.census_population === undefined && (
                            <div className="absolute inset-0 bg-purple-50/50 flex justify-center items-center rounded-md"><RefreshCcw className="w-4 h-4 animate-spin text-purple-400" /></div>
                          )}
                          <p className="text-[10px] text-purple-600 font-bold uppercase tracking-wider mb-1">Population</p>
                          <p className="text-2xl font-black text-gray-800">
                            {parseMetric(reportData.metrics?.census_population)}
                          </p>
                        </div>
                        <div className="bg-emerald-50/50 p-3 rounded-md border border-emerald-100/50 relative">
                          {loading && reportData.metrics?.census_median_income === undefined && (
                            <div className="absolute inset-0 bg-emerald-50/50 flex justify-center items-center rounded-md"><RefreshCcw className="w-4 h-4 animate-spin text-emerald-400" /></div>
                          )}
                          <p className="text-[10px] text-emerald-600 font-bold uppercase tracking-wider mb-1">Median Income</p>
                          <p className="text-2xl font-black text-gray-800">
                            {parseMetric(reportData.metrics?.census_median_income, 'currency')}
                          </p>
                        </div>
                      </div>
                    </div>

                    {/* Nearest POIs List (Paginated) */}
                    {mergedPois.length > 0 && (
                      <div className="pt-4 mt-2 border-t border-gray-100">
                        <div className="flex justify-between items-center mb-3">
                          <h5 className="font-semibold text-gray-800 text-sm flex items-center gap-2">
                            <Store className="w-4 h-4 text-blue-500" />
                            Commercial POIs
                          </h5>
                          <span className="text-xs text-gray-400">
                            {poiPage * POIS_PER_PAGE + 1}-{Math.min((poiPage + 1) * POIS_PER_PAGE, mergedPois.length)} of {mergedPois.length}
                          </span>
                        </div>

                        <div className="space-y-2">
                          {mergedPois
                            .slice(poiPage * POIS_PER_PAGE, (poiPage + 1) * POIS_PER_PAGE)
                            .map((bz: any) => (
                              <div key={bz.id} className="bg-white border border-gray-200 p-3 rounded-md shadow-sm flex items-start justify-between">
                                <div>
                                  <p className="font-bold text-gray-800 text-sm leading-tight">{bz.name}</p>
                                  <p className="text-xs text-gray-500 mt-1">{bz.categories?.[0]?.title || 'Business'}</p>
                                </div>
                                <div className="text-right">
                                  <p className={`text-xs font-bold px-2 py-0.5 rounded border ${bz.rating === 'N/A' ? 'text-gray-500 bg-gray-50 border-gray-200' : 'text-orange-600 bg-orange-50 border-orange-100'}`}>
                                    {bz.rating !== 'N/A' ? `⭐ ${bz.rating}` : 'OSM/Mapbox'}
                                  </p>
                                  <p className="text-[10px] text-gray-400 mt-1">{Math.round(bz.distance)}m away</p>
                                </div>
                              </div>
                            ))}
                        </div>

                        {/* Pagination Controls */}
                        {mergedPois.length > POIS_PER_PAGE && (
                          <div className="flex justify-between items-center mt-3 pt-2 border-t border-gray-50">
                            <button
                              onClick={() => setPoiPage(p => Math.max(0, p - 1))}
                              disabled={poiPage === 0}
                              className="p-1 text-gray-500 hover:bg-gray-100 rounded disabled:opacity-30 disabled:hover:bg-transparent transition-colors"
                            >
                              <ChevronLeft className="w-5 h-5" />
                            </button>
                            <span className="text-xs font-medium text-gray-500 bg-gray-100 px-3 py-1 rounded-full">Page {poiPage + 1}</span>
                            <button
                              onClick={() => setPoiPage(p => Math.min(Math.ceil(mergedPois.length / POIS_PER_PAGE) - 1, p + 1))}
                              disabled={(poiPage + 1) * POIS_PER_PAGE >= mergedPois.length}
                              className="p-1 text-gray-500 hover:bg-gray-100 rounded disabled:opacity-30 disabled:hover:bg-transparent transition-colors"
                            >
                              <ChevronRight className="w-5 h-5" />
                            </button>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              )}
              {/* Aqumen Walkability Index Card (computed from existing data) */}
              {reportData && (() => {
                const osmElements = reportData.raw_data?.osm || [];
                const poisCount = mergedPois.length;
                const transitCount = osmElements.filter((n: any) => n.tags?.highway === 'bus_stop' || n.tags?.railway === 'station').length;
                const parksCount = osmElements.filter((n: any) => n.tags?.leisure === 'park').length;
                const foursquareCount = foursquarePois.length;

                // Scoring: weighted 0-100
                const poiScore = Math.min(poisCount * 2.5, 40);        // up to 40pts for dense POIs
                const fsqScore = Math.min(foursquareCount * 1.5, 15);  // up to 15pts for Foursquare density
                const transitScore = Math.min(transitCount * 4, 25);   // up to 25pts for transit access
                const parksScore = Math.min(parksCount * 5, 10);       // up to 10pts for parks
                const isoScore = isochrone ? 10 : 0;                   // 10pts if isochrone computed (dense enough)
                const total = Math.round(Math.min(poiScore + fsqScore + transitScore + parksScore + isoScore, 100));

                const label = total >= 85 ? 'Walker\'s Paradise' : total >= 70 ? 'Very Walkable' : total >= 50 ? 'Somewhat Walkable' : total >= 25 ? 'Car Dependent' : 'Very Car Dependent';
                const barColor = total >= 70 ? 'bg-emerald-500' : total >= 50 ? 'bg-yellow-400' : 'bg-red-400';

                return (
                  <div className="mt-4 bg-white rounded-lg border border-gray-100 shadow-sm p-4">
                    <h4 className="text-sm font-semibold text-gray-800 mb-2 flex items-center gap-2">
                      <Bike className="w-4 h-4 text-sky-500" /> Aqumen Walkability Index
                    </h4>
                    <div className="flex items-end gap-3 mb-2">
                      <span className="text-4xl font-bold text-blue-600">{total}</span>
                      <span className="text-sm font-medium text-gray-600 mb-1">/100 · {label}</span>
                    </div>
                    <div className="w-full bg-gray-100 rounded-full h-2 mb-3">
                      <div className={`${barColor} h-2 rounded-full transition-all duration-700`} style={{ width: `${total}%` }} />
                    </div>
                    <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs text-gray-500">
                      <span>🏪 POIs nearby: <strong>{poisCount}</strong></span>
                      <span>🚌 Transit stops: <strong>{transitCount}</strong></span>
                      <span>🌳 Parks: <strong>{parksCount}</strong></span>
                      <span>📍 Foursquare: <strong>{foursquareCount}</strong></span>
                    </div>
                  </div>
                );
              })()}
              {/* Crime Data Card */}
              {crimeData && !crimeData.error && (
                <div className="mt-4 bg-white rounded-lg border border-red-100/60 shadow-sm p-4">
                  <h4 className="text-sm font-semibold text-gray-800 mb-1 flex items-center gap-2">
                    <Shield className="w-4 h-4 text-red-500" /> Safety — Last 12 Months
                  </h4>
                  <p className="text-xs text-gray-500 mb-3">{crimeData.total_incidents} incidents within {radius}m</p>
                  <div className="space-y-1.5">
                    {crimeData.categories?.map((cat: any) => {
                      const pct = crimeData.total_incidents > 0 ? Math.round((cat.count / crimeData.total_incidents) * 100) : 0;
                      return (
                        <div key={cat.name}>
                          <div className="flex justify-between text-xs mb-0.5">
                            <span className="text-gray-700 truncate max-w-[70%]">{cat.name}</span>
                            <span className="text-gray-500 font-mono">{cat.count}</span>
                          </div>
                          <div className="w-full bg-red-50 rounded-full h-1.5">
                            <div className="bg-red-400 h-1.5 rounded-full" style={{ width: `${pct}%` }} />
                          </div>
                        </div>
                      );
                    })}
                  </div>
                  <p className="text-[10px] text-gray-400 mt-2">Source: Seattle Open Data. Enable Crime layer to see map pins.</p>
                </div>
              )}
            </div>
          ) : (
            <div className="text-center py-16 text-gray-400 border-2 border-dashed border-gray-200 rounded-xl mt-4">
              <MapPin className="mx-auto h-8 w-8 mb-3 opacity-50" />
              <p className="text-sm px-4">Click anywhere on the map to set a location pin.</p>
            </div>
          )}
        </div>
      </div>

      {/* Map Area */}
      <div className="flex-1 relative bg-gray-200">
        {/* Floating Reset Button */}
        <div className="absolute top-4 right-4 z-10">
          <button
            onClick={handleResetMap}
            className="flex items-center gap-2 bg-white text-gray-700 hover:text-blue-600 px-4 py-2 rounded-md shadow-md border border-gray-200 transition-colors text-sm font-medium"
          >
            <RefreshCcw className="w-4 h-4" />
            Reset Map
          </button>
        </div>

        {MAPBOX_TOKEN ? (
          <Map
            ref={mapRef}
            {...viewState}
            onMove={(evt: ViewStateChangeEvent) => setViewState(evt.viewState)}
            onClick={handleMapClick}
            style={{ width: '100%', height: '100%' }}
            mapStyle="mapbox://styles/mapbox/light-v11"
            mapboxAccessToken={MAPBOX_TOKEN}
            cursor="crosshair"
          >
            <ScaleControl position="bottom-right" />

            {/* Draw Radius Circle if pin is dropped */}
            {pinData && (
              <Source id="radius-source" type="geojson" data={turf.circle([pinData.lng, pinData.lat], radius, { steps: 64, units: 'meters' })}>
                <Layer
                  id="radius-layer-fill"
                  type="fill"
                  paint={{ 'fill-color': '#3b82f6', 'fill-opacity': 0.1 }}
                />
                <Layer
                  id="radius-layer-line"
                  type="line"
                  paint={{ 'line-color': '#3b82f6', 'line-width': 2, 'line-opacity': 0.5, 'line-dasharray': [2, 2] }}
                />
              </Source>
            )}

            {pinData && (
              <Marker longitude={pinData.lng} latitude={pinData.lat} anchor="bottom">
                <MapPin className="text-red-500 h-10 w-10 drop-shadow-lg -ml-5 -mt-10" strokeWidth={2.5} fill="white" />
              </Marker>
            )}

            {/* Isochrone walkshed polygons (5, 10, 15 min walk) */}
            {isochrone && showFilters.isochrone && (
              <Source id="isochrone-source" type="geojson" data={isochrone}>
                <Layer
                  id="isochrone-fill"
                  type="fill"
                  paint={{
                    'fill-color': ['get', 'color'],
                    'fill-opacity': 0.18
                  }}
                />
                <Layer
                  id="isochrone-line"
                  type="line"
                  paint={{ 'line-color': ['get', 'color'], 'line-width': 1.5, 'line-opacity': 0.6 }}
                />
              </Source>
            )}

            {/* Sound Transit Light Rail — static GeoJSON from public folder */}
            {showFilters.lightRail && (
              <Source id="light-rail-source" type="geojson" data="/link_light_rail.geojson">
                <Layer
                  id="light-rail-line"
                  type="line"
                  filter={['==', ['get', 'feature_type'], 'route']}
                  paint={{
                    'line-color': ['coalesce', ['get', 'route_color'], '#00A550'],
                    'line-width': 3.5,
                    'line-opacity': 0.85
                  }}
                />
              </Source>
            )}

            {/* Business Markers */}
            {showFilters.commercial && mergedPois.map((bz: any) => {
              if (!bz.lng || !bz.lat) return null;

              // Determine icon based on categories
              let Icon = Store;
              let iconColor = "text-blue-500";
              const cats = (bz.categories || []).map((c: any) => typeof c === 'string' ? c.toLowerCase() : (c.alias || c.title || '').toLowerCase()).join(" ");

              if (cats.includes("coffee") || cats.includes("cafe")) {
                Icon = Coffee;
                iconColor = "text-amber-600";
              } else if (cats.includes("restaurant") || cats.includes("food") || cats.includes("dining")) {
                Icon = Utensils;
                iconColor = "text-orange-500";
              } else if (cats.includes("gym") || cats.includes("active") || cats.includes("fitness")) {
                Icon = Dumbbell;
                iconColor = "text-purple-500";
              } else if (cats.includes("school") || cats.includes("education")) {
                Icon = BookOpen;
                iconColor = "text-indigo-500";
              }

              return (
                <Marker key={bz.id} longitude={bz.lng} latitude={bz.lat} anchor="bottom">
                  <div className={`bg-white p-1 rounded-full shadow-md border ${iconColor.replace('text', 'border')} group relative cursor-pointer`}>
                    <Icon className={`w-4 h-4 ${iconColor}`} />

                    {/* Tooltip on hover */}
                    <div className="absolute bottom-full mb-2 left-1/2 -translate-x-1/2 hidden group-hover:block w-max max-w-[150px] bg-gray-900 text-white text-xs p-2 rounded shadow-xl z-50">
                      <p className="font-bold truncate">{bz.name}</p>
                      <p>{bz.rating !== 'N/A' ? `⭐ ${bz.rating}` : 'OSM/Mapbox'}</p>
                      <div className="absolute -bottom-1 left-1/2 -translate-x-1/2 w-2 h-2 bg-gray-900 rotate-45"></div>
                    </div>
                  </div>
                </Marker>
              );
            })}

            {/* OSM Structural Markers */}
            {reportData?.raw_data?.osm?.map((node: any) => {
              // Extract lat/lng which could be on the object or its center
              const lat = node.lat || node.center?.lat;
              const lon = node.lon || node.center?.lon;

              if (!lat || !lon) return null;

              let Icon = MapPin;
              let bgColor = "bg-gray-100";
              let textColor = "text-gray-500";
              let label = "OSM Node";
              let desc = "";

              if (node.tags?.highway === 'bus_stop' || node.tags?.railway === 'station') {
                if (!showFilters.transit) return null;
                Icon = Bus;
                bgColor = "bg-teal-100";
                textColor = "text-teal-700";

                const stopName = node.tags.name || "Transit Stop";
                const ref = node.tags.ref ? ` #${node.tags.ref}` : '';
                label = `${stopName}${ref}`;

                const routes = node.tags.route_ref;
                if (routes) {
                  desc = `Served by routes: ${routes}`;
                } else if (node.tags.operator) {
                  desc = `Operated by: ${node.tags.operator}`;
                }
              } else if (node.tags?.leisure === 'park') {
                if (!showFilters.parks) return null;
                Icon = TreePine;
                bgColor = "bg-green-100";
                textColor = "text-green-700";
                label = node.tags.name || "Public Park";
                desc = "Green space for recreation.";
              } else if (node.tags?.amenity === 'school' || node.tags?.amenity === 'library' || node.tags?.amenity === 'townhall') {
                if (!showFilters.civic) return null;
                Icon = BookOpen;
                bgColor = "bg-indigo-100";
                textColor = "text-indigo-700";
                label = node.tags.name || "Civic Institution";
                desc = "Educational/Civic facility.";
              } else {
                return null;
              }

              return (
                <Marker key={node.id} longitude={lon} latitude={lat} anchor="center">
                  <div className={`p-1.5 rounded-full shadow-sm border border-white ${bgColor} group relative cursor-pointer`}>
                    <Icon className={`w-3.5 h-3.5 ${textColor}`} />

                    <div className="absolute bottom-full mb-1.5 left-1/2 -translate-x-1/2 hidden group-hover:block w-max max-w-[200px] bg-white text-gray-800 text-xs p-2 rounded shadow-lg border border-gray-100 z-50">
                      <p className="font-semibold">{label}</p>
                      {desc && <p className="text-gray-500 mt-1 whitespace-normal leading-relaxed">{desc}</p>}
                      <div className="absolute -bottom-1 left-1/2 -translate-x-1/2 w-2 h-2 bg-white border-b border-r border-gray-100 rotate-45"></div>
                    </div>
                  </div>
                </Marker>
              );
            })}

            {/* Crime Incident Markers */}
            {showFilters.crime && crimeData?.incidents?.map((incident: any, i: number) => (
              <Marker key={`crime-${i}`} longitude={incident.lng} latitude={incident.lat} anchor="center">
                <div className="group relative cursor-pointer">
                  <div className="w-2.5 h-2.5 rounded-full bg-red-500 border border-white opacity-70 hover:opacity-100 transition-opacity" />
                  <div className="absolute bottom-full mb-1 left-1/2 -translate-x-1/2 hidden group-hover:block w-max max-w-[160px] bg-gray-900 text-white text-xs p-1.5 rounded shadow-xl z-50">
                    <p className="font-semibold">{incident.category}</p>
                    <p className="text-gray-300">{incident.date}</p>
                    <div className="absolute -bottom-1 left-1/2 -translate-x-1/2 w-2 h-2 bg-gray-900 rotate-45" />
                  </div>
                </div>
              </Marker>
            ))}
          </Map>
        ) : (
          <div className="flex items-center justify-center h-full">
            <p className="text-gray-500 bg-white p-4 rounded shadow-sm">
              ⚠️ Mapbox Token is missing in .env
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;
