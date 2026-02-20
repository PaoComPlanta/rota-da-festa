"use client";

import { useState, useEffect, useCallback, useRef, useMemo } from "react";

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
function parseEventDate(eventDate: string, eventTime: string): Date | null {
  if (!eventDate) return null;
  const parts = eventDate.split("-");
  if (parts.length !== 3) return null;
  const [y, m, d] = parts.map(Number);
  if (isNaN(y) || isNaN(m) || isNaN(d)) return null;
  const timeParts = (eventTime || "00:00").split(":").map(Number);
  const h = isNaN(timeParts[0]) ? 0 : timeParts[0];
  const min = isNaN(timeParts[1]) ? 0 : timeParts[1];
  return new Date(y, m - 1, d, h, min, 0);
}

function getCountdown(eventDate: string, eventTime: string): { text: string; color: string; emoji: string } {
  const eventDt = parseEventDate(eventDate, eventTime);
  if (!eventDt || isNaN(eventDt.getTime())) {
    return { text: "Data por confirmar", color: "text-gray-400 dark:text-gray-500", emoji: "❓" };
  }

  const now = new Date();
  const diffMs = eventDt.getTime() - now.getTime();
  const diffMinutes = Math.floor(diffMs / (1000 * 60));
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60));

  // Already passed
  if (diffMs < -2 * 60 * 60 * 1000) {
    return { text: "Já decorreu", color: "text-gray-400 dark:text-gray-500", emoji: "⏰" };
  }

  // Currently happening (within ~2h of start)
  if (diffMs < 0) {
    return { text: "A decorrer agora!", color: "text-red-600 dark:text-red-400", emoji: "🔴" };
  }

  // Less than 1 hour
  if (diffMinutes < 60) {
    return { text: `Começa em ${diffMinutes} min`, color: "text-red-600 dark:text-red-400", emoji: "🔴" };
  }

  // Today — show hours
  const todayStr = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`;
  if (eventDate === todayStr) {
    return {
      text: diffHours === 1 ? `Hoje, falta 1 hora` : `Hoje, faltam ${diffHours}h`,
      color: "text-green-600 dark:text-green-400",
      emoji: "🟢",
    };
  }

  // Tomorrow
  const tomorrow = new Date(now);
  tomorrow.setDate(tomorrow.getDate() + 1);
  const tomorrowStr = `${tomorrow.getFullYear()}-${String(tomorrow.getMonth() + 1).padStart(2, "0")}-${String(tomorrow.getDate()).padStart(2, "0")}`;
  if (eventDate === tomorrowStr) {
    return { text: `Amanhã às ${eventTime}`, color: "text-blue-600 dark:text-blue-400", emoji: "📣" };
  }

  // Calculate days from today (midnight to midnight)
  const todayMidnight = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const eventMidnight = new Date(eventDt.getFullYear(), eventDt.getMonth(), eventDt.getDate());
  const diffDays = Math.round((eventMidnight.getTime() - todayMidnight.getTime()) / (1000 * 60 * 60 * 24));

  if (diffDays <= 7) {
    return { text: `Faltam ${diffDays} dias`, color: "text-indigo-600 dark:text-indigo-400", emoji: "📅" };
  }
  return { text: `Faltam ${diffDays} dias`, color: "text-gray-600 dark:text-gray-300", emoji: "🗓" };
}

function generateICS(event: any): string {
  const dtStart = event.data.replace(/-/g, "") + "T" + (event.hora || "00:00").replace(":", "") + "00";
  const startDate = parseEventDate(event.data, event.hora) || new Date();
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

function getDistanceBetween(lat1: number, lon1: number, lat2: number, lon2: number) {
  const R = 6371;
  const dLat = ((lat2 - lat1) * Math.PI) / 180;
  const dLon = ((lon2 - lon1) * Math.PI) / 180;
  const a = Math.sin(dLat / 2) ** 2 + Math.cos((lat1 * Math.PI) / 180) * Math.cos((lat2 * Math.PI) / 180) * Math.sin(dLon / 2) ** 2;
  return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

function buildTeamUrl(event: any, isHome: boolean): string {
  const directUrl = isHome ? event.url_equipa_casa : event.url_equipa_fora;
  if (directUrl) return directUrl;
  // Fallback: pesquisa direta no ZeroZero (não Google)
  const team = isHome ? event.equipa_casa : event.equipa_fora;
  return `https://www.zerozero.pt/search.php?search=${encodeURIComponent(team)}`;
}

function buildClassificationUrl(event: any): string {
  // URL direto da classificação (extraído pelo scraper)
  if (event.url_classificacao) return event.url_classificacao;

  // Fallback: pesquisa no ZeroZero (não Google)
  let comp = event.categoria || "";
  if (comp.startsWith("Formação")) {
    comp = comp.replace("Formação - ", "").replace(/[()]/g, "").trim();
  }
  return `https://www.zerozero.pt/search.php?search=${encodeURIComponent(comp + " classificação")}`;
}

function formatWeekday(dateStr: string): string {
  const days = ["Domingo", "Segunda-feira", "Terça-feira", "Quarta-feira", "Quinta-feira", "Sexta-feira", "Sábado"];
  const parts = dateStr.split("-").map(Number);
  if (parts.length !== 3 || parts.some(isNaN)) return "";
  const d = new Date(parts[0], parts[1] - 1, parts[2], 12);
  return days[d.getDay()] || "";
}

function formatDateShort(dateStr: string): string {
  const parts = dateStr.split("-");
  if (parts.length !== 3) return dateStr;
  return `${parts[2]}/${parts[1]}/${parts[0]}`;
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
  const [isFirstMount, setIsFirstMount] = useState(true);
  const scrollRef = useRef<HTMLDivElement>(null);
  const prevEventId = useRef<number | null>(null);

  const isFutebol = event.tipo === "Futebol";
  const countdown = getCountdown(event.data, event.hora);

  // Scroll to top on event change (no flicker)
  useEffect(() => {
    if (prevEventId.current !== null && prevEventId.current !== event.id) {
      // Switching events — scroll to top smoothly, no entry animation
      scrollRef.current?.scrollTo({ top: 0, behavior: "smooth" });
    }
    prevEventId.current = event.id;
  }, [event.id]);

  // Disable first-mount animation after opening
  useEffect(() => {
    const t = requestAnimationFrame(() => setIsFirstMount(false));
    return () => cancelAnimationFrame(t);
  }, []);

  // Nearby events: same week, within 15km, excluding self
  const nearbyEvents = useMemo(() =>
    allEvents
      .filter((ev) => {
        if (ev.id === event.id) return false;
        const dist = getDistanceBetween(event.latitude, event.longitude, ev.latitude, ev.longitude);
        const d1 = parseEventDate(ev.data, "12:00");
        const d2 = parseEventDate(event.data, "12:00");
        if (!d1 || !d2) return false;
        const daysDiff = Math.abs((d1.getTime() - d2.getTime()) / (1000 * 60 * 60 * 24));
        return dist < 15 && daysDiff <= 7;
      })
      .map((ev) => ({
        ...ev,
        distFromEvent: getDistanceBetween(event.latitude, event.longitude, ev.latitude, ev.longitude),
      }))
      .sort((a, b) => a.distFromEvent - b.distFromEvent)
      .slice(0, 5),
    [allEvents, event.id, event.latitude, event.longitude, event.data]
  );

  // Fetch weather from Open-Meteo (reset on event change)
  useEffect(() => {
    setWeather(null);
    const eventDt = parseEventDate(event.data, "12:00");
    if (!eventDt) return;
    const now = new Date();
    const diffDays = Math.ceil((eventDt.getTime() - now.getTime()) / (1000 * 60 * 60 * 24));

    if (diffDays < -1 || diffDays > 14) return;

    setWeatherLoading(true);
    let cancelled = false;
    const url = `https://api.open-meteo.com/v1/forecast?latitude=${event.latitude}&longitude=${event.longitude}&daily=temperature_2m_max,temperature_2m_min,weathercode&timezone=Europe/Lisbon&start_date=${event.data}&end_date=${event.data}`;

    fetch(url)
      .then((r) => r.json())
      .then((data) => {
        if (cancelled) return;
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
      .finally(() => { if (!cancelled) setWeatherLoading(false); });

    return () => { cancelled = true; };
  }, [event.id, event.data, event.latitude, event.longitude]);

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
      text: `${event.nome} — ${formatDateShort(event.data)} às ${event.hora} em ${event.local}`,
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
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm transition-opacity" onClick={onClose} />

      {/* Modal — only animate on first mount */}
      <div className={`relative w-full md:max-w-lg md:mx-4 max-h-[90vh] bg-white dark:bg-gray-900 rounded-t-2xl md:rounded-2xl shadow-2xl overflow-hidden flex flex-col ${isFirstMount ? "animate-slide-up" : ""}`}>
        
        {/* Drag handle (mobile) */}
        <div className="flex justify-center pt-2 pb-0 md:hidden">
          <div className="w-10 h-1 rounded-full bg-gray-300 dark:bg-gray-700" />
        </div>

        {/* Header — transition content smoothly */}
        <div className={`p-4 pb-3 border-b border-gray-100 dark:border-gray-800 transition-colors duration-200 ${isFutebol ? "bg-gradient-to-r from-green-50 to-blue-50 dark:from-green-950/30 dark:to-blue-950/30" : "bg-gradient-to-r from-red-50 to-orange-50 dark:from-red-950/30 dark:to-orange-950/30"}`}>
          <div className="flex justify-between items-center mb-2">
            <button onClick={onClose} className="p-1.5 rounded-full bg-gray-200/80 dark:bg-gray-700/80 hover:bg-gray-300 dark:hover:bg-gray-600 transition-colors" aria-label="Fechar">
              <svg className="w-5 h-5 text-gray-600 dark:text-gray-300" fill="none" viewBox="0 0 24 24" strokeWidth={2.5} stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" /></svg>
            </button>
            <div className="flex items-center gap-2">
              <span className={`text-xs font-bold px-2.5 py-1 rounded-full bg-white/80 dark:bg-gray-800/80 ${countdown.color} transition-colors duration-200`}>
                {countdown.emoji} {countdown.text}
              </span>
              <button onClick={onToggleFavorite} className={`p-2 rounded-full transition-all duration-200 ${isFavorite ? "text-red-500 bg-red-50 dark:bg-red-900/30 scale-110" : "text-gray-400 bg-gray-100 dark:bg-gray-800 hover:scale-110"}`} aria-label="Favorito">
                <svg xmlns="http://www.w3.org/2000/svg" fill={isFavorite ? "currentColor" : "none"} viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" className="w-5 h-5">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M21 8.25c0-2.485-2.099-4.5-4.688-4.5-1.935 0-3.597 1.126-4.312 2.733-.715-1.607-2.377-2.733-4.313-2.733C5.1 3.75 3 5.765 3 8.25c0 7.22 9 12 9 12s9-4.78 9-12z" />
                </svg>
              </button>
            </div>
          </div>

          <div className="flex items-center gap-2 mb-2 flex-wrap">
            <span className={`text-[10px] uppercase font-bold px-2 py-0.5 rounded-full tracking-wider transition-colors duration-200 ${isFutebol ? "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-100" : "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-100"}`}>
              {event.tipo}
            </span>
            {event.escalao && (
              <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full transition-colors duration-200 ${event.escalao === "Seniores" ? "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-100" : "bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-100"}`}>
                {event.escalao}
              </span>
            )}
            {event.categoria && (
              <span className="text-[10px] font-medium px-2 py-0.5 rounded-full bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400">
                {event.categoria}
              </span>
            )}
          </div>

          <h2 className="text-xl font-extrabold text-gray-900 dark:text-white leading-tight">
            {event.nome}
          </h2>
        </div>

        {/* Scrollable Content */}
        <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 space-y-4 scroll-smooth">

          {/* Adiado Banner */}
          {event.status === "adiado" && (
            <div className="bg-orange-50 dark:bg-orange-950/30 border border-orange-200 dark:border-orange-800 rounded-xl p-3 flex items-center gap-3">
              <span className="text-2xl">⚠️</span>
              <div>
                <p className="font-bold text-orange-800 dark:text-orange-200 text-sm">Jogo Adiado</p>
                <p className="text-xs text-orange-600 dark:text-orange-400">
                  {event.descricao?.includes("Remarcado para")
                    ? event.descricao.split(".")[0]
                    : "Este jogo foi adiado. Consulta o ZeroZero para mais informações."}
                </p>
              </div>
            </div>
          )}

          {/* Quick Actions */}
          <div className="grid grid-cols-4 gap-2">
            <button onClick={() => { onShowOnMap(event); onClose(); }} className="flex flex-col items-center gap-1 p-3 rounded-xl bg-blue-50 dark:bg-blue-950/30 hover:bg-blue-100 dark:hover:bg-blue-900/30 transition-colors group active:scale-95">
              <span className="text-xl group-hover:scale-110 transition-transform">🗺️</span>
              <span className="text-[10px] font-bold text-blue-700 dark:text-blue-300">Ver Mapa</span>
            </button>
            <button onClick={handleNavigate} className="flex flex-col items-center gap-1 p-3 rounded-xl bg-green-50 dark:bg-green-950/30 hover:bg-green-100 dark:hover:bg-green-900/30 transition-colors group active:scale-95">
              <span className="text-xl group-hover:scale-110 transition-transform">🚗</span>
              <span className="text-[10px] font-bold text-green-700 dark:text-green-300">Ir Para Lá</span>
            </button>
            <button onClick={handleCalendar} className="flex flex-col items-center gap-1 p-3 rounded-xl bg-purple-50 dark:bg-purple-950/30 hover:bg-purple-100 dark:hover:bg-purple-900/30 transition-colors group active:scale-95">
              <span className="text-xl group-hover:scale-110 transition-transform">📅</span>
              <span className="text-[10px] font-bold text-purple-700 dark:text-purple-300">Calendário</span>
            </button>
            <button onClick={handleShare} className="flex flex-col items-center gap-1 p-3 rounded-xl bg-orange-50 dark:bg-orange-950/30 hover:bg-orange-100 dark:hover:bg-orange-900/30 transition-colors group active:scale-95 relative">
              <span className="text-xl group-hover:scale-110 transition-transform">📤</span>
              <span className="text-[10px] font-bold text-orange-700 dark:text-orange-300">{shareMsg || "Partilhar"}</span>
            </button>
          </div>

          {/* Info Grid */}
          <div className="bg-gray-50 dark:bg-gray-800/50 rounded-xl p-4 space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <div className="flex items-center gap-2">
                <span className="text-lg">📍</span>
                <div className="min-w-0">
                  <p className="text-[10px] text-gray-500 dark:text-gray-400 font-medium uppercase">Local</p>
                  <p className="text-sm font-bold text-gray-900 dark:text-white truncate">{event.local}</p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-lg">📅</span>
                <div>
                  <p className="text-[10px] text-gray-500 dark:text-gray-400 font-medium uppercase">Data</p>
                  <p className="text-sm font-bold text-gray-900 dark:text-white">{formatWeekday(event.data)}, {formatDateShort(event.data)}</p>
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

          {/* Weather — fixed height to prevent layout shift */}
          <div className="min-h-[80px] rounded-xl overflow-hidden transition-all duration-300">
            {weatherLoading ? (
              <div className="bg-gradient-to-r from-sky-50 to-blue-50 dark:from-sky-950/30 dark:to-blue-950/30 rounded-xl p-4">
                <h3 className="text-xs font-bold text-gray-500 dark:text-gray-400 uppercase mb-2">🌤 Previsão Meteorológica</h3>
                <div className="flex items-center gap-2 text-sm text-gray-400">
                  <span className="animate-pulse">⏳</span> A carregar previsão...
                </div>
              </div>
            ) : weather ? (
              <div className="bg-gradient-to-r from-sky-50 to-blue-50 dark:from-sky-950/30 dark:to-blue-950/30 rounded-xl p-4">
                <h3 className="text-xs font-bold text-gray-500 dark:text-gray-400 uppercase mb-2">🌤 Previsão Meteorológica</h3>
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
              </div>
            ) : null}
          </div>

          {/* Football Section */}
          {isFutebol && (
            <div className="bg-gradient-to-r from-green-50 to-emerald-50 dark:from-green-950/20 dark:to-emerald-950/20 rounded-xl p-4">
              <h3 className="text-xs font-bold text-gray-500 dark:text-gray-400 uppercase mb-3">⚽ Informação do Jogo</h3>
              
              {(event.equipa_casa || event.equipa_fora) ? (
                <div className="flex items-center justify-between mb-3">
                  <div className="flex-1 text-center min-w-0">
                    <p className="font-extrabold text-gray-900 dark:text-white text-base truncate px-1">{event.equipa_casa}</p>
                    <a href={buildTeamUrl(event, true)} target="_blank" rel="noopener noreferrer" className="text-[10px] text-blue-600 dark:text-blue-400 hover:underline font-medium">
                      Ver no ZeroZero →
                    </a>
                  </div>
                  <div className="px-3 flex-shrink-0">
                    <span className="text-2xl font-black text-gray-300 dark:text-gray-600">VS</span>
                  </div>
                  <div className="flex-1 text-center min-w-0">
                    <p className="font-extrabold text-gray-900 dark:text-white text-base truncate px-1">{event.equipa_fora}</p>
                    <a href={buildTeamUrl(event, false)} target="_blank" rel="noopener noreferrer" className="text-[10px] text-blue-600 dark:text-blue-400 hover:underline font-medium">
                      Ver no ZeroZero →
                    </a>
                  </div>
                </div>
              ) : null}

              {event.descricao && (
                <p className="text-xs text-gray-600 dark:text-gray-400 bg-white/50 dark:bg-gray-800/50 rounded-lg p-2 text-center">
                  {event.descricao}
                </p>
              )}

              {/* Classification — uses Google site:zerozero.pt for precise results */}
              {event.categoria && (
                <a
                  href={buildClassificationUrl(event)}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="mt-3 flex items-center justify-center gap-2 p-2.5 rounded-lg bg-white/70 dark:bg-gray-800/70 hover:bg-white dark:hover:bg-gray-800 transition-colors text-sm font-bold text-gray-700 dark:text-gray-200 active:scale-[0.98]"
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
                    className="w-full text-left p-3 rounded-xl bg-gray-50 dark:bg-gray-800/50 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors flex items-center gap-3 group active:scale-[0.98]"
                  >
                    <span className="text-xl flex-shrink-0">{ev.tipo === "Futebol" ? "⚽" : "🎉"}</span>
                    <div className="flex-1 min-w-0">
                      <p className="font-bold text-sm text-gray-900 dark:text-white truncate group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors">
                        {ev.nome}
                      </p>
                      <p className="text-[11px] text-gray-500 dark:text-gray-400">
                        {formatDateShort(ev.data)} · {ev.hora} · {ev.distFromEvent.toFixed(1)} km
                      </p>
                    </div>
                    <svg className="w-4 h-4 text-gray-400 flex-shrink-0" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5" /></svg>
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Bottom spacer for safe area */}
          <div className="h-2" />
        </div>
      </div>
    </div>
  );
}
