"use client";

import { useState, useEffect, useCallback } from "react";

// =============================================
// Types
// =============================================
interface EventDetailModalProps {
  event: any;
  distance: number | null;
  userLocation: { lat: number; lng: number } | null;
  userId: string | null;
  isFavorite: boolean;
  allEvents: any[];
  onClose: () => void;
  onToggleFavorite: () => void;
  onShowOnMap: (event: any) => void;
  onSelectEvent: (event: any) => void;
}

interface WeatherData {
  tempMax: number;
  tempMin: number;
  code: number;
  icon: string;
  desc: string;
}

// =============================================
// Weather codes (WMO standard, used by Open-Meteo)
// =============================================
const WEATHER_DESC: Record<number, { icon: string; desc: string }> = {
  0: { icon: "☀️", desc: "Céu limpo" },
  1: { icon: "🌤", desc: "Poucas nuvens" },
  2: { icon: "⛅", desc: "Parcialmente nublado" },
  3: { icon: "☁️", desc: "Nublado" },
  45: { icon: "🌫", desc: "Nevoeiro" },
  48: { icon: "🌫", desc: "Nevoeiro gelado" },
  51: { icon: "🌦", desc: "Chuviscos ligeiros" },
  53: { icon: "🌦", desc: "Chuviscos" },
  55: { icon: "🌧", desc: "Chuviscos fortes" },
  61: { icon: "🌧", desc: "Chuva ligeira" },
  63: { icon: "🌧", desc: "Chuva moderada" },
  65: { icon: "🌧", desc: "Chuva forte" },
  71: { icon: "🌨", desc: "Neve ligeira" },
  73: { icon: "🌨", desc: "Neve moderada" },
  75: { icon: "❄️", desc: "Neve forte" },
  80: { icon: "🌦", desc: "Aguaceiros ligeiros" },
  81: { icon: "🌧", desc: "Aguaceiros" },
  82: { icon: "⛈", desc: "Aguaceiros fortes" },
  95: { icon: "⛈", desc: "Trovoada" },
  96: { icon: "⛈", desc: "Trovoada com granizo" },
  99: { icon: "⛈", desc: "Trovoada forte" },
};

// =============================================
// Helpers
// =============================================
function getCountdown(eventDate: string, eventTime: string): { text: string; color: string; emoji: string } {
  const now = new Date();
  const eventDt = new Date(`${eventDate}T${eventTime || "00:00"}:00`);
  const diffMs = eventDt.getTime() - now.getTime();
  const diffDays = Math.ceil(diffMs / (1000 * 60 * 60 * 24));

  if (diffDays < 0) return { text: "Já decorreu", color: "text-gray-400 dark:text-gray-500", emoji: "⏰" };
  if (diffDays === 0) return { text: `Hoje às ${eventTime}`, color: "text-green-600 dark:text-green-400", emoji: "🔴" };
  if (diffDays === 1) return { text: `Amanhã às ${eventTime}`, color: "text-blue-600 dark:text-blue-400", emoji: "📣" };
  if (diffDays <= 7) return { text: `Faltam ${diffDays} dias`, color: "text-indigo-600 dark:text-indigo-400", emoji: "📅" };
  return { text: `Faltam ${diffDays} dias`, color: "text-gray-600 dark:text-gray-300", emoji: "🗓" };
}

function generateICS(event: any): string {
  const dtStart = event.data.replace(/-/g, "") + "T" + (event.hora || "00:00").replace(":", "") + "00";
  const startDate = new Date(`${event.data}T${event.hora || "00:00"}:00`);
  const endDate = new Date(startDate.getTime() + 2 * 60 * 60 * 1000);
  const pad = (n: number) => String(n).padStart(2, "0");
  const dtEnd = `${endDate.getFullYear()}${pad(endDate.getMonth() + 1)}${pad(endDate.getDate())}T${pad(endDate.getHours())}${pad(endDate.getMinutes())}00`;

  return [
    "BEGIN:VCALENDAR",
    "VERSION:2.0",
    "PRODID:-//Rota da Festa//PT",
    "BEGIN:VEVENT",
    `DTSTART:${dtStart}`,
    `DTEND:${dtEnd}`,
    `SUMMARY:${event.nome}`,
    `LOCATION:${event.local}`,
    `DESCRIPTION:${event.descricao || event.categoria || ""}`,
    `GEO:${event.latitude};${event.longitude}`,
    "END:VEVENT",
    "END:VCALENDAR",
  ].join("\r\n");
}

function getDistance(lat1: number, lon1: number, lat2: number, lon2: number) {
  const R = 6371;
  const dLat = ((lat2 - lat1) * Math.PI) / 180;
  const dLon = ((lon2 - lon1) * Math.PI) / 180;
  const a = Math.sin(dLat / 2) ** 2 + Math.cos((lat1 * Math.PI) / 180) * Math.cos((lat2 * Math.PI) / 180) * Math.sin(dLon / 2) ** 2;
  return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

function buildZeroZeroSearch(team: string): string {
  return `https://www.zerozero.pt/search.php?search=${encodeURIComponent(team)}`;
}

function formatWeekday(dateStr: string): string {
  const days = ["Domingo", "Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado"];
  const d = new Date(dateStr + "T12:00:00");
  return days[d.getDay()];
}

// =============================================
// Component
// =============================================
export default function EventDetailModal({
  event, distance, userLocation, userId, isFavorite,
  allEvents, onClose, onToggleFavorite, onShowOnMap, onSelectEvent,
}: EventDetailModalProps) {
  const [weather, setWeather] = useState<WeatherData | null>(null);
  const [weatherLoading, setWeatherLoading] = useState(false);
  const [shareMsg, setShareMsg] = useState("");

  const isFutebol = event.tipo === "Futebol";
  const countdown = getCountdown(event.data, event.hora);

  // Nearby events: same week, within 15km, excluding self
  const nearbyEvents = allEvents
    .filter((ev) => {
      if (ev.id === event.id) return false;
      const dist = getDistance(event.latitude, event.longitude, ev.latitude, ev.longitude);
      const daysDiff = Math.abs(
        (new Date(ev.data).getTime() - new Date(event.data).getTime()) / (1000 * 60 * 60 * 24)
      );
      return dist < 15 && daysDiff <= 7;
    })
    .map((ev) => ({
      ...ev,
      distFromEvent: getDistance(event.latitude, event.longitude, ev.latitude, ev.longitude),
    }))
    .sort((a, b) => a.distFromEvent - b.distFromEvent)
    .slice(0, 5);

  // Fetch weather from Open-Meteo
  useEffect(() => {
    const eventDate = new Date(event.data + "T12:00:00");
    const now = new Date();
    const diffDays = Math.ceil((eventDate.getTime() - now.getTime()) / (1000 * 60 * 60 * 24));

    if (diffDays < 0 || diffDays > 14) return;

    setWeatherLoading(true);
    const url = `https://api.open-meteo.com/v1/forecast?latitude=${event.latitude}&longitude=${event.longitude}&daily=temperature_2m_max,temperature_2m_min,weathercode&timezone=Europe/Lisbon&start_date=${event.data}&end_date=${event.data}`;

    fetch(url)
      .then((r) => r.json())
      .then((data) => {
        if (data.daily?.temperature_2m_max?.[0] != null) {
          const code = data.daily.weathercode[0];
          const wd = WEATHER_DESC[code] || { icon: "🌡", desc: "Desconhecido" };
          setWeather({
            tempMax: Math.round(data.daily.temperature_2m_max[0]),
            tempMin: Math.round(data.daily.temperature_2m_min[0]),
            code,
            icon: wd.icon,
            desc: wd.desc,
          });
        }
      })
      .catch(() => {})
      .finally(() => setWeatherLoading(false));
  }, [event.data, event.latitude, event.longitude]);

  // Close on Escape
  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [onClose]);

  // Prevent body scroll when modal is open
  useEffect(() => {
    document.body.style.overflow = "hidden";
    return () => { document.body.style.overflow = ""; };
  }, []);

  const handleShare = useCallback(async () => {
    const shareData = {
      title: event.nome,
      text: `${event.nome} — ${event.data} às ${event.hora} em ${event.local}`,
      url: window.location.href,
    };
    try {
      if (navigator.share) {
        await navigator.share(shareData);
      } else {
        await navigator.clipboard.writeText(shareData.text);
        setShareMsg("Copiado!");
        setTimeout(() => setShareMsg(""), 2000);
      }
    } catch {
      // User cancelled share
    }
  }, [event]);

  const handleCalendar = useCallback(() => {
    const ics = generateICS(event);
    const blob = new Blob([ics], { type: "text/calendar;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${event.nome.replace(/[^a-zA-Z0-9À-ÿ ]/g, "").trim()}.ics`;
    a.click();
    URL.revokeObjectURL(url);
  }, [event]);

  const handleNavigate = () => {
    const url = userLocation
      ? `https://www.google.com/maps/dir/?api=1&origin=${userLocation.lat},${userLocation.lng}&destination=${event.latitude},${event.longitude}`
      : `https://www.google.com/maps/dir/?api=1&destination=${event.latitude},${event.longitude}`;
    window.open(url, "_blank");
  };

  return (
    <div className="fixed inset-0 z-50 flex items-end md:items-center justify-center" role="dialog" aria-modal="true">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={onClose} />

      {/* Modal */}
      <div className="relative w-full md:max-w-lg md:mx-4 max-h-[90vh] bg-white dark:bg-gray-900 rounded-t-2xl md:rounded-2xl shadow-2xl overflow-hidden flex flex-col animate-slide-up">
        
        {/* Header */}
        <div className={`p-4 pb-3 border-b border-gray-100 dark:border-gray-800 ${isFutebol ? "bg-gradient-to-r from-green-50 to-blue-50 dark:from-green-950/30 dark:to-blue-950/30" : "bg-gradient-to-r from-red-50 to-orange-50 dark:from-red-950/30 dark:to-orange-950/30"}`}>
          {/* Close + Favorite */}
          <div className="flex justify-between items-center mb-2">
            <button onClick={onClose} className="p-1.5 rounded-full bg-gray-200/80 dark:bg-gray-700/80 hover:bg-gray-300 dark:hover:bg-gray-600 transition-colors" aria-label="Fechar">
              <svg className="w-5 h-5 text-gray-600 dark:text-gray-300" fill="none" viewBox="0 0 24 24" strokeWidth={2.5} stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" /></svg>
            </button>
            <div className="flex items-center gap-2">
              {/* Countdown badge */}
              <span className={`text-xs font-bold px-2.5 py-1 rounded-full bg-white/80 dark:bg-gray-800/80 ${countdown.color}`}>
                {countdown.emoji} {countdown.text}
              </span>
              <button onClick={onToggleFavorite} className={`p-2 rounded-full transition-colors ${isFavorite ? "text-red-500 bg-red-50 dark:bg-red-900/30" : "text-gray-400 bg-gray-100 dark:bg-gray-800"}`} aria-label="Favorito">
                <svg xmlns="http://www.w3.org/2000/svg" fill={isFavorite ? "currentColor" : "none"} viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" className="w-5 h-5">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M21 8.25c0-2.485-2.099-4.5-4.688-4.5-1.935 0-3.597 1.126-4.312 2.733-.715-1.607-2.377-2.733-4.313-2.733C5.1 3.75 3 5.765 3 8.25c0 7.22 9 12 9 12s9-4.78 9-12z" />
                </svg>
              </button>
            </div>
          </div>

          {/* Badges */}
          <div className="flex items-center gap-2 mb-2 flex-wrap">
            <span className={`text-[10px] uppercase font-bold px-2 py-0.5 rounded-full tracking-wider ${isFutebol ? "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-100" : "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-100"}`}>
              {event.tipo}
            </span>
            {event.escalao && (
              <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${event.escalao === "Seniores" ? "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-100" : "bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-100"}`}>
                {event.escalao}
              </span>
            )}
            {event.categoria && (
              <span className="text-[10px] font-medium px-2 py-0.5 rounded-full bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400">
                {event.categoria}
              </span>
            )}
          </div>

          {/* Title */}
          <h2 className="text-xl font-extrabold text-gray-900 dark:text-white leading-tight">
            {event.nome}
          </h2>
        </div>

        {/* Scrollable Content */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">

          {/* Quick Actions */}
          <div className="grid grid-cols-4 gap-2">
            <button onClick={() => { onShowOnMap(event); onClose(); }} className="flex flex-col items-center gap-1 p-3 rounded-xl bg-blue-50 dark:bg-blue-950/30 hover:bg-blue-100 dark:hover:bg-blue-900/30 transition-colors group">
              <span className="text-xl group-hover:scale-110 transition-transform">🗺️</span>
              <span className="text-[10px] font-bold text-blue-700 dark:text-blue-300">Ver Mapa</span>
            </button>
            <button onClick={handleNavigate} className="flex flex-col items-center gap-1 p-3 rounded-xl bg-green-50 dark:bg-green-950/30 hover:bg-green-100 dark:hover:bg-green-900/30 transition-colors group">
              <span className="text-xl group-hover:scale-110 transition-transform">🚗</span>
              <span className="text-[10px] font-bold text-green-700 dark:text-green-300">Ir Para Lá</span>
            </button>
            <button onClick={handleCalendar} className="flex flex-col items-center gap-1 p-3 rounded-xl bg-purple-50 dark:bg-purple-950/30 hover:bg-purple-100 dark:hover:bg-purple-900/30 transition-colors group">
              <span className="text-xl group-hover:scale-110 transition-transform">📅</span>
              <span className="text-[10px] font-bold text-purple-700 dark:text-purple-300">Calendário</span>
            </button>
            <button onClick={handleShare} className="flex flex-col items-center gap-1 p-3 rounded-xl bg-orange-50 dark:bg-orange-950/30 hover:bg-orange-100 dark:hover:bg-orange-900/30 transition-colors group relative">
              <span className="text-xl group-hover:scale-110 transition-transform">📤</span>
              <span className="text-[10px] font-bold text-orange-700 dark:text-orange-300">{shareMsg || "Partilhar"}</span>
            </button>
          </div>

          {/* Info Grid */}
          <div className="bg-gray-50 dark:bg-gray-800/50 rounded-xl p-4 space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <div className="flex items-center gap-2">
                <span className="text-lg">📍</span>
                <div>
                  <p className="text-[10px] text-gray-500 dark:text-gray-400 font-medium uppercase">Local</p>
                  <p className="text-sm font-bold text-gray-900 dark:text-white">{event.local}</p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-lg">📅</span>
                <div>
                  <p className="text-[10px] text-gray-500 dark:text-gray-400 font-medium uppercase">Data</p>
                  <p className="text-sm font-bold text-gray-900 dark:text-white">{formatWeekday(event.data)}, {event.data}</p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-lg">🕒</span>
                <div>
                  <p className="text-[10px] text-gray-500 dark:text-gray-400 font-medium uppercase">Hora</p>
                  <p className="text-sm font-bold text-gray-900 dark:text-white">{event.hora}</p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-lg">💰</span>
                <div>
                  <p className="text-[10px] text-gray-500 dark:text-gray-400 font-medium uppercase">Preço</p>
                  <p className="text-sm font-bold text-gray-900 dark:text-white">
                    {event.preco}
                    {event.preco?.includes("estimado") && <span className="text-[9px] text-amber-500 ml-1">⚠ média</span>}
                  </p>
                </div>
              </div>
            </div>
            {distance != null && (
              <div className="flex items-center gap-2 pt-2 border-t border-gray-200 dark:border-gray-700">
                <span className="text-lg">📏</span>
                <p className="text-sm text-gray-600 dark:text-gray-300">
                  <span className="font-bold">{distance.toFixed(1)} km</span> da tua localização
                </p>
              </div>
            )}
          </div>

          {/* Weather */}
          {(weather || weatherLoading) && (
            <div className="bg-gradient-to-r from-sky-50 to-blue-50 dark:from-sky-950/30 dark:to-blue-950/30 rounded-xl p-4">
              <h3 className="text-xs font-bold text-gray-500 dark:text-gray-400 uppercase mb-2">🌤 Previsão Meteorológica</h3>
              {weatherLoading ? (
                <div className="flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400">
                  <span className="animate-spin">⏳</span> A carregar...
                </div>
              ) : weather ? (
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <span className="text-4xl">{weather.icon}</span>
                    <div>
                      <p className="font-bold text-gray-900 dark:text-white text-lg">{weather.desc}</p>
                      <p className="text-sm text-gray-500 dark:text-gray-400">Para o dia do evento</p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="text-2xl font-extrabold text-gray-900 dark:text-white">{weather.tempMax}°</p>
                    <p className="text-sm text-gray-400">{weather.tempMin}°</p>
                  </div>
                </div>
              ) : null}
            </div>
          )}

          {/* Football Section */}
          {isFutebol && (
            <div className="bg-gradient-to-r from-green-50 to-emerald-50 dark:from-green-950/20 dark:to-emerald-950/20 rounded-xl p-4">
              <h3 className="text-xs font-bold text-gray-500 dark:text-gray-400 uppercase mb-3">⚽ Informação do Jogo</h3>
              
              {/* Teams */}
              {(event.equipa_casa || event.equipa_fora) ? (
                <div className="flex items-center justify-between mb-3">
                  <div className="flex-1 text-center">
                    <p className="font-extrabold text-gray-900 dark:text-white text-base">{event.equipa_casa}</p>
                    <a href={buildZeroZeroSearch(event.equipa_casa)} target="_blank" rel="noopener noreferrer" className="text-[10px] text-blue-600 dark:text-blue-400 hover:underline font-medium">
                      Ver no ZeroZero →
                    </a>
                  </div>
                  <div className="px-4">
                    <span className="text-2xl font-black text-gray-300 dark:text-gray-600">VS</span>
                  </div>
                  <div className="flex-1 text-center">
                    <p className="font-extrabold text-gray-900 dark:text-white text-base">{event.equipa_fora}</p>
                    <a href={buildZeroZeroSearch(event.equipa_fora)} target="_blank" rel="noopener noreferrer" className="text-[10px] text-blue-600 dark:text-blue-400 hover:underline font-medium">
                      Ver no ZeroZero →
                    </a>
                  </div>
                </div>
              ) : null}

              {/* Competition info */}
              {event.descricao && (
                <p className="text-xs text-gray-600 dark:text-gray-400 bg-white/50 dark:bg-gray-800/50 rounded-lg p-2 text-center">
                  {event.descricao}
                </p>
              )}

              {/* ZeroZero classification link */}
              {event.categoria && (
                <a
                  href={`https://www.zerozero.pt/search.php?search=${encodeURIComponent(event.categoria)}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="mt-3 flex items-center justify-center gap-2 p-2.5 rounded-lg bg-white/70 dark:bg-gray-800/70 hover:bg-white dark:hover:bg-gray-800 transition-colors text-sm font-bold text-gray-700 dark:text-gray-200"
                >
                  📊 Ver Classificação — {event.categoria}
                </a>
              )}
            </div>
          )}

          {/* Description (non-football) */}
          {!isFutebol && event.descricao && (
            <div className="bg-gray-50 dark:bg-gray-800/50 rounded-xl p-4">
              <h3 className="text-xs font-bold text-gray-500 dark:text-gray-400 uppercase mb-2">📝 Descrição</h3>
              <p className="text-sm text-gray-700 dark:text-gray-300 leading-relaxed">{event.descricao}</p>
            </div>
          )}

          {/* Nearby Events */}
          {nearbyEvents.length > 0 && (
            <div>
              <h3 className="text-xs font-bold text-gray-500 dark:text-gray-400 uppercase mb-2">📍 Eventos Por Perto</h3>
              <div className="space-y-2">
                {nearbyEvents.map((ev) => (
                  <button
                    key={ev.id}
                    onClick={() => onSelectEvent(ev)}
                    className="w-full text-left p-3 rounded-xl bg-gray-50 dark:bg-gray-800/50 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors flex items-center gap-3 group"
                  >
                    <span className="text-xl flex-shrink-0">{ev.tipo === "Futebol" ? "⚽" : "🎉"}</span>
                    <div className="flex-1 min-w-0">
                      <p className="font-bold text-sm text-gray-900 dark:text-white truncate group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors">
                        {ev.nome}
                      </p>
                      <p className="text-[11px] text-gray-500 dark:text-gray-400">
                        {ev.data} · {ev.hora} · {ev.distFromEvent.toFixed(1)} km
                      </p>
                    </div>
                    <svg className="w-4 h-4 text-gray-400 flex-shrink-0" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5" /></svg>
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
