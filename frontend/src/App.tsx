import { useState } from 'react';
import Map, { Marker } from 'react-map-gl';
import type { ViewStateChangeEvent, MapLayerMouseEvent } from 'react-map-gl';
import 'mapbox-gl/dist/mapbox-gl.css';
import { MapPin, RefreshCcw } from 'lucide-react';

const MAPBOX_TOKEN = import.meta.env.VITE_MAPBOX_TOKEN;

const DEFAULT_VIEW_STATE = {
  longitude: -122.3321, // Seattle Longitude
  latitude: 47.6062,    // Seattle Latitude
  zoom: 12
};

function App() {
  const [viewState, setViewState] = useState(DEFAULT_VIEW_STATE);

  const [pinData, setPinData] = useState<{ lat: number, lng: number } | null>(null);
  const [reportData, setReportData] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleMapClick = (evt: MapLayerMouseEvent) => {
    setPinData({
      lng: evt.lngLat.lng,
      lat: evt.lngLat.lat
    });
    setReportData(null); // Clear previous report when new pin drops
    setError(null);
  };

  const handleResetMap = () => {
    setViewState(DEFAULT_VIEW_STATE);
    setPinData(null);
    setReportData(null);
    setError(null);
  };

  const generateReport = async () => {
    if (!pinData) return;

    setLoading(true);
    setError(null);

    try {
      const response = await fetch(`${import.meta.env.VITE_API_URL}/api/report`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(pinData)
      });

      if (!response.ok) {
        throw new Error(`API responded with status: ${response.status}`);
      }

      const data = await response.json();
      setReportData(data);
    } catch (err: any) {
      setError(err.message || "Failed to connect to backend API.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex h-screen w-full font-sans bg-gray-50">
      {/* Sidebar / Report Card Area */}
      <div className="w-96 bg-white shadow-xl z-10 flex flex-col pt-8 border-r border-gray-200">
        <h1 className="text-2xl font-bold px-6 text-gray-800 tracking-tight">Aqumen</h1>
        <p className="text-sm text-gray-500 px-6 mt-2 pb-6 border-b border-gray-100">
          Drop a pin on the map to generate a micro-locality report card for any business.
        </p>

        <div className="flex-1 overflow-y-auto px-6 mt-6">
          {pinData ? (
            <div className="bg-blue-50 border border-blue-100 rounded-lg p-5">
              <h3 className="font-semibold text-blue-900 mb-2">Location Selected</h3>
              <div className="space-y-1">
                <p className="text-sm text-blue-700 font-mono">Lat: {pinData.lat.toFixed(4)}</p>
                <p className="text-sm text-blue-700 font-mono">Lng: {pinData.lng.toFixed(4)}</p>
              </div>
              <button
                onClick={generateReport}
                disabled={loading}
                className="mt-6 w-full bg-blue-600 hover:bg-blue-700 disabled:bg-blue-300 text-white font-medium py-2.5 px-4 rounded-md shadow-sm transition-colors flex justify-center items-center">
                {loading ? (
                  <span className="animate-pulse">Analyzing Area...</span>
                ) : "Generate Report"}
              </button>

              {error && (
                <div className="mt-4 p-3 bg-red-50 text-red-700 text-sm rounded border border-red-200">
                  {error}
                </div>
              )}

              {reportData && (
                <div className="mt-6 p-4 bg-white border border-gray-200 rounded-lg shadow-sm">
                  <h4 className="font-bold text-gray-800 border-b pb-2 mb-3">API Response Success!</h4>
                  <pre className="text-xs text-gray-600 bg-gray-50 p-2 rounded overflow-x-auto">
                    {JSON.stringify(reportData, null, 2)}
                  </pre>
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
            {...viewState}
            onMove={(evt: ViewStateChangeEvent) => setViewState(evt.viewState)}
            onClick={handleMapClick}
            style={{ width: '100%', height: '100%' }}
            mapStyle="mapbox://styles/mapbox/light-v11"
            mapboxAccessToken={MAPBOX_TOKEN}
            cursor="crosshair"
          >
            {pinData && (
              <Marker longitude={pinData.lng} latitude={pinData.lat} anchor="bottom">
                <MapPin className="text-red-500 h-10 w-10 drop-shadow-lg -ml-5 -mt-10" strokeWidth={2.5} fill="white" />
              </Marker>
            )}
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
