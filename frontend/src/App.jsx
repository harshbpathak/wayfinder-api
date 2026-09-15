import { useCallback, useState } from 'react';
import { CircleMarker, MapContainer, Polyline, Popup, TileLayer, useMap } from 'react-leaflet';

const DEFAULT_ORIGIN = [31.7017559, 76.5228147];
const SUGGESTIONS = ['CSE department', 'Vivekananda Lecture Hall Complex', 'Central Library', 'Kailash Hostel', 'Health Centre'];

function RouteViewport({ route }) {
  const map = useMap();
  if (route?.length > 1) map.fitBounds(route, { padding: [42, 42] });
  return null;
}

function formatResponse(data) {
  if (!data.found) return {
    type: 'error',
    text: data.candidates?.length
      ? `I could not identify one place. Did you mean: ${data.candidates.join(', ')}?`
      : 'I could not find that campus location. Try a department, hostel, gate, or facility name.'
  };
  return { type: 'answer', data };
}

export default function App() {
  const [query, setQuery] = useState('');
  const [origin, setOrigin] = useState(DEFAULT_ORIGIN);
  const [originLabel, setOriginLabel] = useState('Gate 1 (default)');
  const [message, setMessage] = useState({ type: 'info', text: 'Ask where you want to go. Your route will be drawn on the map.' });
  const [route, setRoute] = useState(null);
  const [destination, setDestination] = useState(null);
  const [loading, setLoading] = useState(false);

  const findRoute = useCallback(async (value = query) => {
    const place = value.trim();
    if (!place || loading) return;
    setQuery('');
    setLoading(true);
    setMessage({ type: 'loading', text: `Finding ${place}…` });
    try {
      const params = new URLSearchParams({ query: place, origin_lat: String(origin[0]), origin_lon: String(origin[1]) });
      const response = await fetch(`/locate?${params}`);
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || 'The location service did not respond.');
      const next = formatResponse(data);
      setMessage(next);
      if (data.found) {
        setDestination([data.destination.latitude, data.destination.longitude]);
        setRoute(data.route?.geometry?.coordinates?.map(([longitude, latitude]) => [latitude, longitude]) ?? null);
      } else {
        setRoute(null);
        setDestination(null);
      }
    } catch (error) {
      setMessage({ type: 'error', text: error.message });
      setRoute(null);
    } finally {
      setLoading(false);
    }
  }, [loading, origin, query]);

  const useCurrentLocation = () => {
    if (!navigator.geolocation) {
      setMessage({ type: 'error', text: 'This browser does not support location access. The route will start from Gate 1.' });
      return;
    }
    setMessage({ type: 'loading', text: 'Requesting your current location…' });
    navigator.geolocation.getCurrentPosition(
      ({ coords }) => {
        setOrigin([coords.latitude, coords.longitude]);
        setOriginLabel('Your current location');
        setMessage({ type: 'info', text: 'Current location set. Search for a destination to draw the route.' });
      },
      () => setMessage({ type: 'error', text: 'Location access was unavailable. The route will start from Gate 1.' }),
      { enableHighAccuracy: true, timeout: 10000, maximumAge: 60000 }
    );
  };

  const answer = message.type === 'answer' ? message.data : null;
  return <main className="app-shell">
    <header>
      <div><p className="eyebrow">NIT Hamirpur</p><h1>Campus Wayfinder</h1></div>
      <span className="online"><i /> Route service online</span>
    </header>
    <section className="layout">
      <aside className="chat-panel">
        <div className="intro-card"><strong>Ask naturally.</strong><p>“Where is the Vivekananda Lecture Hall Complex?”</p></div>
        <div className={`message ${message.type}`}>
          {answer ? <>
            <p className="place">{answer.name}</p>
            <p>{answer.directions || 'A route could not be calculated.'}</p>
            {answer.route && <div className="chips"><span>{answer.route.distance_km} km</span><span>{answer.route.duration_minutes} min</span><span>{answer.route.compass_direction}</span></div>}
            {answer.maps_link && <a href={answer.maps_link} target="_blank" rel="noreferrer">Open in OpenStreetMap ↗</a>}
          </> : <p>{message.text}</p>}
        </div>
        <div className="suggestions">{SUGGESTIONS.map(s => <button key={s} onClick={() => findRoute(s)}>{s}</button>)}</div>
        <form onSubmit={(event) => { event.preventDefault(); findRoute(); }} className="search-form">
          <div className="location-status"><span>📍</span><span>Starting from: {originLabel}</span><button type="button" onClick={useCurrentLocation}>Use my location</button></div>
          <div className="input-row"><input value={query} onChange={e => setQuery(e.target.value)} placeholder="Ask for a campus destination…" aria-label="Campus destination" /><button disabled={loading} type="submit">{loading ? '…' : 'Find route'}</button></div>
        </form>
      </aside>
      <section className="map-panel" aria-label="Campus route map">
        <div className="map-caption">OpenStreetMap · OSRM routing</div>
        <MapContainer center={[31.7074, 76.5263]} zoom={16} scrollWheelZoom className="map">
          <TileLayer attribution="&copy; <a href='https://www.openstreetmap.org/copyright'>OpenStreetMap</a> contributors" url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
          <CircleMarker center={origin} radius={8} pathOptions={{ color: '#ffffff', weight: 3, fillColor: '#31d19b', fillOpacity: 1 }}><Popup>Your starting point</Popup></CircleMarker>
          {destination && <CircleMarker center={destination} radius={9} pathOptions={{ color: '#ffffff', weight: 3, fillColor: '#638cff', fillOpacity: 1 }}><Popup>{answer?.name}</Popup></CircleMarker>}
          {route && <><Polyline positions={route} pathOptions={{ color: '#6b8cff', weight: 6, opacity: 0.9 }} /><RouteViewport route={route} /></>}
        </MapContainer>
      </section>
    </section>
  </main>;
}
