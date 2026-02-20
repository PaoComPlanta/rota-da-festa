"use client";

import { MapContainer, TileLayer, Marker, Popup, useMap } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import L from "leaflet";
import { useEffect, useState } from "react";
import { useTheme } from "./ThemeProvider";

// Tipos
interface Evento {
  id: number;
  nome: string;
  latitude: number;
  longitude: number;
  tipo: string;
  escalao: string | null;
  data: string;
  hora: string;
  local: string;
  preco: string;
}

interface MapProps {
  events: Evento[];
  userLocation: { lat: number; lng: number } | null;
  onSelectEvent?: (event: Evento) => void;
}

// Ícones Customizados
const createIcon = (tipo: string) => {
  const isFutebol = tipo === "Futebol";
  return L.divIcon({
    className: "custom-icon",
    html: `<div style="
      background-color: ${isFutebol ? "#22c55e" : "#ef4444"};
      width: 32px;
      height: 32px;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      border: 3px solid white;
      box-shadow: 0 4px 6px rgba(0,0,0,0.3);
      font-size: 18px;
    ">${isFutebol ? "⚽" : "🎉"}</div>`,
    iconSize: [32, 32],
    iconAnchor: [16, 32],
    popupAnchor: [0, -32],
  });
};

function RecenterMap({ lat, lng }: { lat: number; lng: number }) {
  const map = useMap();
  useEffect(() => {
    map.setView([lat, lng], map.getZoom());
  }, [lat, lng, map]);
  return null;
}

export default function Map({ events, userLocation, onSelectEvent }: MapProps) {
  const { theme } = useTheme();
  
  // Tiles Baseados no Tema
  const lightTiles = "https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png";
  const darkTiles = "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png";

  // Braga por defeito se não houver userLocation
  const defaultCenter = { lat: 41.5503, lng: -8.4270 };
  const center = userLocation || defaultCenter;

  return (
    <div className="h-full w-full relative z-0 bg-gray-200 dark:bg-gray-900 transition-colors">
      <MapContainer
        center={[center.lat, center.lng]}
        zoom={12}
        scrollWheelZoom={true}
        style={{ height: "100%", width: "100%" }}
        className="outline-none focus:ring-2 focus:ring-blue-500"
      >
        <TileLayer
          attribution='&copy; <a href="https://carto.com/">CARTO</a>'
          url={theme === "dark" ? darkTiles : lightTiles}
        />

        {/* Marcador do Utilizador */}
        {userLocation && (
          <Marker
            position={[userLocation.lat, userLocation.lng]}
            icon={L.divIcon({
              className: "user-icon",
              html: '<div style="background:#3b82f6; width:18px; height:18px; border-radius:50%; border:3px solid white; box-shadow:0 0 0 4px rgba(59,130,246,0.4);"></div>',
              iconSize: [18, 18],
            })}
          >
            <Popup>
              <span className="font-bold text-gray-800">Estás aqui! 📍</span>
            </Popup>
          </Marker>
        )}

        {/* Marcadores dos Eventos */}
        {events.map((event) => (
          <Marker
            key={event.id}
            position={[event.latitude, event.longitude]}
            icon={createIcon(event.tipo)}
          >
            <Popup>
              <div className="min-w-[180px] p-1 font-sans">
                <h3 className="font-bold text-gray-900 text-base mb-1">{event.nome}</h3>
                <p className="text-sm text-gray-600 m-0 font-medium">📍 {event.local}</p>
                <div className="flex items-center gap-2 mt-2 mb-3 text-xs text-gray-500">
                  <span className="bg-gray-100 px-2 py-1 rounded">📅 {event.data}</span>
                  <span className="bg-gray-100 px-2 py-1 rounded">🕒 {event.hora}</span>
                </div>
                <div className="flex gap-2">
                  {onSelectEvent && (
                    <button
                      onClick={() => onSelectEvent(event)}
                      className="flex-1 text-center bg-gray-900 hover:bg-gray-800 text-white font-bold py-2 px-3 rounded-lg transition-colors text-sm"
                    >
                      Detalhes 📋
                    </button>
                  )}
                  <a
                    href={`https://www.google.com/maps/dir/?api=1&destination=${event.latitude},${event.longitude}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex-1 text-center bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-3 rounded-lg transition-colors no-underline text-sm"
                  >
                    Navegar 🚗
                  </a>
                </div>
              </div>
            </Popup>
          </Marker>
        ))}

        {userLocation && <RecenterMap lat={userLocation.lat} lng={userLocation.lng} />}
      </MapContainer>
    </div>
  );
}
