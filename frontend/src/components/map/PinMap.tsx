import 'leaflet/dist/leaflet.css';
import { CircleMarker, MapContainer, TileLayer } from 'react-leaflet';

interface PinMapProps {
  lat: number;
  lon: number;
  /** Accessible description, e.g. "Where the photo was taken". */
  label: string;
}

const OSM_TILES = 'https://tile.openstreetmap.org/{z}/{x}/{y}.png';
const OSM_ATTRIBUTION = '© OpenStreetMap contributors';

/**
 * Read-only map with one pin (wizard review step, docs/05_UI_SPEC.md §4 step 4). OSM tiles with the required credit
 * (§2 "Maps"); no dragging or zooming, so the page scrolls normally over it on a phone. A CircleMarker needs no marker
 * images (the bundler cannot resolve Leaflet's default icon URLs).
 */
export function PinMap({ lat, lon, label }: PinMapProps) {
  return (
    <div role="img" aria-label={label} className="h-48 overflow-hidden rounded-xl border border-slate-200 bg-slate-100">
      <MapContainer
        center={[lat, lon]}
        zoom={17}
        dragging={false}
        scrollWheelZoom={false}
        doubleClickZoom={false}
        touchZoom={false}
        boxZoom={false}
        keyboard={false}
        zoomControl={false}
        className="size-full"
      >
        <TileLayer url={OSM_TILES} attribution={OSM_ATTRIBUTION} />
        <CircleMarker
          center={[lat, lon]}
          radius={10}
          pathOptions={{ color: '#ffffff', weight: 3, fillColor: '#0f766e', fillOpacity: 1 }} // brand-700
        />
      </MapContainer>
    </div>
  );
}
