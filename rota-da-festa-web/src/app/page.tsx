"use client";

import { useEffect, useState, useMemo, useCallback } from "react";
import dynamic from "next/dynamic";
import { supabase } from "@/utils/supabase/client";
import EventCard from "@/components/EventCard";
import EventDetailModal from "@/components/EventDetailModal";
import ChatWidget from "@/components/ChatWidget";
import Link from "next/link";
import { useTheme } from "@/components/ThemeProvider";

const MapComponent = dynamic(() => import("@/components/Map"), {
  ssr: false,
  loading: () => <div className="h-full w-full bg-gray-200 dark:bg-gray-800 animate-pulse flex items-center justify-center text-gray-500 dark:text-gray-400 font-medium">Carregando Mapa...</div>
});

function getDistance(lat1: number, lon1: number, lat2: number, lon2: number) {
  const R = 6371;
  const dLat = ((lat2 - lat1) * Math.PI) / 180;
  const dLon = ((lon2 - lon1) * Math.PI) / 180;
  const a =
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos((lat1 * Math.PI) / 180) *
      Math.cos((lat2 * Math.PI) / 180) *
      Math.sin(dLon / 2) *
      Math.sin(dLon / 2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return R * c;
}

// Centróides dos distritos para atribuir distrito a cada evento via lat/lon
const DISTRICT_CENTROIDS: Record<string, { lat: number; lon: number }> = {
  "Braga": { lat: 41.5503, lon: -8.4270 },
  "Porto": { lat: 41.1496, lon: -8.6109 },
  "Aveiro": { lat: 40.6405, lon: -8.6538 },
  "Lisboa": { lat: 38.7223, lon: -9.1393 },
  "Leiria": { lat: 39.7437, lon: -8.8070 },
  "Coimbra": { lat: 40.2109, lon: -8.4377 },
  "Viseu": { lat: 40.6610, lon: -7.9097 },
  "Setúbal": { lat: 38.5244, lon: -8.8882 },
  "Santarém": { lat: 39.2369, lon: -8.6850 },
  "Beja": { lat: 38.0150, lon: -7.8653 },
  "Faro": { lat: 37.0194, lon: -7.9304 },
  "Évora": { lat: 38.5667, lon: -7.9000 },
  "Bragança": { lat: 41.8063, lon: -6.7572 },
  "Castelo Branco": { lat: 39.8228, lon: -7.4906 },
  "Guarda": { lat: 40.5373, lon: -7.2676 },
  "Viana do Castelo": { lat: 41.6936, lon: -8.8319 },
  "Vila Real": { lat: 41.2959, lon: -7.7464 },
  "Portalegre": { lat: 39.2967, lon: -7.4317 },
  "Madeira": { lat: 32.6669, lon: -16.9241 },
  "Açores": { lat: 37.7483, lon: -25.6666 },
};

function getDistrito(lat: number, lon: number): string {
  let closest = "Outro";
  let minDist = Infinity;
  for (const [name, c] of Object.entries(DISTRICT_CENTROIDS)) {
    const d = getDistance(lat, lon, c.lat, c.lon);
    if (d < minDist) {
      minDist = d;
      closest = name;
    }
  }
  return closest;
}

export default function Home() {
  const { theme, toggleTheme } = useTheme();
  
  // Coordenadas de Braga por defeito
  const DEFAULT_BRAGA = { lat: 41.5503, lng: -8.4270 };
  
  const [events, setEvents] = useState<any[]>([]);
  const [negocios, setNegocios] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [userLocation, setUserLocation] = useState<{ lat: number; lng: number } | null>(DEFAULT_BRAGA);
  const [searchTerm, setSearchTerm] = useState("");
  const [filterType, setFilterType] = useState("Todos");
  const [filterEscalao, setFilterEscalao] = useState("Todos");
  const [activeTab, setActiveTab] = useState<"lista" | "mapa" | "favoritos">("lista");
  const [userId, setUserId] = useState<string | null>(null);
  const [userAvatar, setUserAvatar] = useState<string | null>(null);
  const [userName, setUserName] = useState<string | null>(null);
  const [userFavorites, setUserFavorites] = useState<number[]>(() => {
    if (typeof window !== "undefined") {
      try {
        return JSON.parse(localStorage.getItem("rotadafesta_favs") || "[]");
      } catch { return []; }
    }
    return [];
  });
  const [filterDistrito, setFilterDistrito] = useState("Todos");
  const [filterDate, setFilterDate] = useState("Todos");
  const [citySelection, setCitySelection] = useState("braga");
  const [selectedEvent, setSelectedEvent] = useState<any | null>(null);

  // Callbacks for modal
  const handleSelectEvent = useCallback((event: any) => {
    setSelectedEvent(event);
  }, []);

  const handleShowOnMap = useCallback((event: any) => {
    setUserLocation({ lat: event.latitude, lng: event.longitude });
    setActiveTab("mapa");
  }, []);

  const handleToggleFavorite = useCallback(async (eventId?: number) => {
    const id = eventId ?? selectedEvent?.id;
    if (!id) return;
    const isFav = userFavorites.includes(id);
    
    // Atualizar estado local + localStorage imediatamente (otimistic update)
    const newFavs = isFav ? userFavorites.filter((fid) => fid !== id) : [...userFavorites, id];
    setUserFavorites(newFavs);
    try { localStorage.setItem("rotadafesta_favs", JSON.stringify(newFavs)); } catch {}

    // Sincronizar com Supabase se logado
    if (userId) {
      try {
        if (isFav) {
          const { error } = await supabase.from("favoritos").delete().match({ user_id: userId, evento_id: id });
          if (error) console.error("Erro ao remover favorito:", error.message);
        } else {
          const { error } = await supabase.from("favoritos").insert({ user_id: userId, evento_id: id });
          if (error) console.error("Erro ao adicionar favorito:", error.message);
        }
      } catch (e) {
        console.error("Erro Supabase favoritos:", e);
      }
    }
  }, [userId, selectedEvent, userFavorites]);

  // 1. Setup Inicial
  useEffect(() => {
    supabase.auth.getUser().then(({ data }) => {
      setUserId(data.user?.id || null);
      setUserAvatar(data.user?.user_metadata?.avatar_url || null);
      setUserName(data.user?.user_metadata?.full_name || data.user?.email?.split("@")[0] || null);
      if (data.user) fetchFavorites(data.user.id);
    });
    fetchEvents();
  }, []);

  // Handler de Localização
  const handleLocationChange = (val: string) => {
    setCitySelection(val);
    if (val === "gps") {
      if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(
          (pos) => setUserLocation({ lat: pos.coords.latitude, lng: pos.coords.longitude }),
          (err) => {
            console.error("Erro GPS:", err);
            alert("Não foi possível obter a tua localização. A usar Braga como fallback.");
            setUserLocation(DEFAULT_BRAGA);
            setCitySelection("braga");
          }
        );
      }
    } else {
      const district = Object.entries(DISTRICT_CENTROIDS).find(
        ([name]) => name.toLowerCase().replace(/ /g, "-") === val
      );
      if (district) {
        setUserLocation({ lat: district[1].lat, lng: district[1].lon });
      }
    }
  };

  async function fetchEvents() {
    setLoading(true);
    const [evRes, negRes] = await Promise.all([
      supabase.from("eventos").select("*"),
      supabase.from("negocios").select("*").eq("ativo", true),
    ]);
    if (!evRes.error && evRes.data) setEvents(evRes.data);
    if (!negRes.error && negRes.data) setNegocios(negRes.data);
    setLoading(false);
  }

  async function fetchFavorites(uid: string) {
    try {
      const { data, error } = await supabase.from("favoritos").select("evento_id").eq("user_id", uid);
      if (error) {
        console.error("Erro ao carregar favoritos:", error.message);
        return;
      }
      if (data) {
        const dbFavs = data.map((f: any) => f.evento_id);
        // Merge: localStorage + Supabase (sem duplicados)
        setUserFavorites((prev) => {
          const merged = Array.from(new Set([...prev, ...dbFavs]));
          try { localStorage.setItem("rotadafesta_favs", JSON.stringify(merged)); } catch {}
          return merged;
        });
      }
    } catch (e) {
      console.error("Erro ao carregar favoritos:", e);
    }
  }

  // Calcular distritos disponíveis a partir dos eventos
  const availableDistritos = useMemo(() => {
    const distritos = new Set<string>();
    events.forEach((ev) => {
      if (ev.latitude && ev.longitude) {
        distritos.add(getDistrito(ev.latitude, ev.longitude));
      }
    });
    return Array.from(distritos).sort();
  }, [events]);

  const processedEvents = useMemo(() => {
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const todayStr = today.toISOString().split("T")[0];

    const getEndOfWeekend = () => {
      const d = new Date(today);
      const day = d.getDay(); // 0=Sun
      const daysUntilSun = day === 0 ? 0 : 7 - day;
      d.setDate(d.getDate() + daysUntilSun);
      return d.toISOString().split("T")[0];
    };

    const getEndOfNextWeek = () => {
      const d = new Date(today);
      d.setDate(d.getDate() + 7);
      return d.toISOString().split("T")[0];
    };

    let filtered = events.filter((ev) => {
      const matchesSearch = ev.nome.toLowerCase().includes(searchTerm.toLowerCase());
      const matchesType = filterType === "Todos" || (() => {
        const tipo = (ev.tipo || "").toLowerCase();
        const cat = (ev.categoria || "").toLowerCase();
        switch (filterType) {
          case "Futebol": return tipo === "futebol" || tipo.includes("futebol");
          case "Festas": return tipo === "festa" || cat.includes("festa") || cat.includes("romaria") || cat.includes("tradição");
          case "Concertos": return tipo === "concerto" || cat.includes("concerto") || cat.includes("música") || cat.includes("festival");
          case "Feiras": return tipo === "feira" || cat.includes("feira") || cat.includes("gastronomia") || cat.includes("mercado");
          case "Cultura": return tipo === "cultura" || cat.includes("teatro") || cat.includes("exposição") || cat.includes("cultural");
          default: return true;
        }
      })();
      const matchesEscalao = filterEscalao === "Todos" || ev.escalao === filterEscalao;
      const matchesDistrito = filterDistrito === "Todos" || (ev.latitude && ev.longitude && getDistrito(ev.latitude, ev.longitude) === filterDistrito);
      const matchesDate = filterDate === "Todos" || (() => {
        const evDate = ev.data;
        if (!evDate) return true;
        switch (filterDate) {
          case "Hoje": return evDate === todayStr;
          case "FDS": return evDate >= todayStr && evDate <= getEndOfWeekend();
          case "Semana": return evDate >= todayStr && evDate <= getEndOfNextWeek();
          default: return true;
        }
      })();
      const isVisible = ev.status === "aprovado" || ev.status === "adiado";
      return matchesSearch && matchesType && matchesEscalao && matchesDistrito && matchesDate && isVisible;
    });

    if (userLocation) {
      filtered = filtered.map((ev) => ({
        ...ev,
        distance: getDistance(userLocation.lat, userLocation.lng, ev.latitude, ev.longitude),
      })).sort((a, b) => a.distance - b.distance);
    } else {
        filtered.sort((a, b) => new Date(a.data).getTime() - new Date(b.data).getTime());
    }

    // Adiados sempre no fim da lista
    filtered.sort((a, b) => {
      if (a.status === "adiado" && b.status !== "adiado") return 1;
      if (a.status !== "adiado" && b.status === "adiado") return -1;
      return 0;
    });

    return filtered;
  }, [events, userLocation, searchTerm, filterType, filterEscalao, filterDistrito, filterDate]);

  return (
    <div className="h-screen w-screen flex flex-col overflow-hidden bg-gray-50 dark:bg-gray-950 text-gray-900 dark:text-gray-100 transition-colors duration-300">
      
      {/* HEADER ACESSÍVEL */}
      <header className="bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-800 px-4 py-3 flex justify-between items-center z-20 shadow-sm transition-colors">
        <div className="flex items-center gap-2">
          <span className="text-2xl" role="img" aria-label="Logo">🎉</span>
          <h1 className="text-xl font-extrabold tracking-tight bg-gradient-to-r from-green-600 to-blue-600 bg-clip-text text-transparent hidden sm:block">
            Rota da Festa
          </h1>
          {processedEvents.length > 0 && (
            <span className="hidden sm:inline-flex text-[10px] font-bold bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400 px-2 py-0.5 rounded-full">
              {processedEvents.length} eventos
            </span>
          )}
        </div>

        <div className="flex items-center gap-3">
          {/* Seletor de Cidade */}
          <select
            value={citySelection}
            onChange={(e) => handleLocationChange(e.target.value)}
            className="bg-gray-100 dark:bg-gray-800 text-gray-800 dark:text-gray-200 text-sm rounded-lg px-3 py-2 border-none focus:ring-2 focus:ring-blue-500 outline-none font-medium cursor-pointer transition-colors"
            aria-label="Escolher localização"
          >
            <option value="gps">🎯 Minha Localização</option>
            {Object.keys(DISTRICT_CENTROIDS).map((name) => (
              <option key={name} value={name.toLowerCase().replace(/ /g, "-")}>📍 {name}</option>
            ))}
          </select>

          {/* Botão de Tema */}
          <button
            onClick={toggleTheme}
            className="p-2 rounded-full bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors focus:ring-2 focus:ring-blue-500 focus:outline-none"
            aria-label={theme === "light" ? "Mudar para modo escuro" : "Mudar para modo claro"}
          >
            {theme === "light" ? "🌙" : "☀️"}
          </button>

          {/* Submeter Evento */}
          <Link
            href="/submit"
            className="hidden sm:flex items-center gap-1 text-xs font-bold text-green-700 dark:text-green-400 bg-green-100 dark:bg-green-900/30 px-3 py-2 rounded-lg hover:bg-green-200 dark:hover:bg-green-800/40 transition-colors"
          >
            ➕ Submeter
          </Link>

          {/* User Status */}
          {userId ? (
             <div className="flex items-center gap-2">
               {userAvatar && (
                 <img src={userAvatar} alt="" className="w-7 h-7 rounded-full border-2 border-green-500" referrerPolicy="no-referrer" />
               )}
               <span className="hidden sm:block text-xs font-semibold text-green-600 dark:text-green-400 max-w-[80px] truncate">
                 {userName}
               </span>
               <button
                 onClick={async () => { await supabase.auth.signOut(); setUserId(null); setUserAvatar(null); setUserName(null); }}
                 className="text-[10px] text-gray-400 hover:text-red-500 dark:hover:text-red-400 transition-colors"
                 title="Sair"
               >
                 Sair
               </button>
             </div>
          ) : (
             <Link 
               href="/login" 
               className="text-sm bg-black dark:bg-white text-white dark:text-black font-bold px-4 py-2 rounded-lg hover:opacity-90 transition-opacity focus:ring-2 focus:ring-blue-500 focus:outline-none"
             >
               Entrar
             </Link>
          )}
        </div>
      </header>

      {/* MAIN CONTENT */}
      <main className="flex-1 relative flex flex-col md:flex-row overflow-hidden bg-gray-50 dark:bg-gray-950 transition-colors">
        
        {/* COLUNA ESQUERDA: LISTA & FILTROS */}
        <div className={`
            w-full md:w-1/3 lg:w-1/4 h-full bg-white dark:bg-gray-900 flex flex-col border-r border-gray-200 dark:border-gray-800 z-10 transition-colors
            ${activeTab === 'mapa' ? 'hidden md:flex' : 'flex'}
        `}>
          {/* Área de Filtros */}
          <div className="p-4 border-b border-gray-200 dark:border-gray-800 space-y-3 bg-white dark:bg-gray-900 transition-colors">
            <div className="relative">
              <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400">🔍</span>
              <input
                type="text"
                placeholder="Pesquisar equipas, festas..."
                className="w-full bg-gray-100 dark:bg-gray-800 text-gray-900 dark:text-white border-none rounded-lg pl-10 pr-4 py-2.5 focus:ring-2 focus:ring-blue-500 outline-none transition-colors placeholder-gray-500 dark:placeholder-gray-400 font-medium"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                aria-label="Pesquisar eventos"
              />
            </div>
            
            <div className="flex gap-2 overflow-x-auto pb-1 hide-scrollbar" role="tablist" aria-label="Filtros de tipo">
              {[
                { label: "Todos", icon: "🌟" },
                { label: "Futebol", icon: "⚽" },
                { label: "Festas", icon: "🎪" },
                { label: "Concertos", icon: "🎵" },
                { label: "Feiras", icon: "🍖" },
                { label: "Cultura", icon: "🎭" },
              ].map(({ label, icon }) => {
                const isActive = filterType === label;
                return (
                  <button
                    key={label}
                    role="tab"
                    aria-selected={isActive}
                    onClick={() => { setFilterType(label); if (label !== "Futebol") setFilterEscalao("Todos"); }}
                    className={`
                      px-3 py-1.5 rounded-full text-xs font-bold whitespace-nowrap transition-all focus:ring-2 focus:ring-blue-500 focus:outline-none flex items-center gap-1
                      ${isActive 
                        ? "bg-black dark:bg-white text-white dark:text-black shadow-md" 
                        : "bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700"
                      }
                    `}
                  >
                    <span>{icon}</span> {label}
                  </button>
                );
              })}
            </div>

            {/* Filtro de Escalão (só visível para Futebol ou Todos) */}
            {(filterType === "Todos" || filterType === "Futebol") && (
              <div className="flex gap-2 overflow-x-auto pb-1 hide-scrollbar" role="tablist" aria-label="Filtros de escalão">
                {["Todos", "Seniores", "Sub-23", "Sub-19", "Sub-17", "Sub-15", "Sub-13", "Benjamins", "Traquinas"].map((esc) => {
                  const isActive = filterEscalao === esc;
                  return (
                    <button
                      key={esc}
                      role="tab"
                      aria-selected={isActive}
                      onClick={() => setFilterEscalao(esc)}
                      className={`
                        px-3 py-1 rounded-full text-[10px] font-bold whitespace-nowrap transition-all focus:ring-2 focus:ring-blue-500 focus:outline-none
                        ${isActive
                          ? "bg-blue-600 text-white shadow-md"
                          : "bg-gray-100 dark:bg-gray-800 text-gray-500 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-700"
                        }
                      `}
                    >
                      {esc}
                    </button>
                  );
                })}
              </div>
            )}

            {/* Filtro por Distrito */}
            {availableDistritos.length > 0 && (
              <select
                value={filterDistrito}
                onChange={(e) => setFilterDistrito(e.target.value)}
                className="w-full bg-gray-100 dark:bg-gray-800 text-gray-800 dark:text-gray-200 text-sm rounded-lg px-3 py-2 border-none focus:ring-2 focus:ring-blue-500 outline-none font-medium cursor-pointer transition-colors"
                aria-label="Filtrar por distrito"
              >
                <option value="Todos">📍 Todos os distritos</option>
                {availableDistritos.map((d) => (
                  <option key={d} value={d}>{d}</option>
                ))}
              </select>
            )}

            {/* Filtro por Data */}
            <div className="flex gap-2" role="tablist" aria-label="Filtros de data">
              {[
                { label: "Todos", icon: "📅" },
                { label: "Hoje", icon: "🔴" },
                { label: "FDS", icon: "🎉" },
                { label: "Semana", icon: "🗓" },
              ].map(({ label, icon }) => {
                const isActive = filterDate === label;
                return (
                  <button
                    key={label}
                    role="tab"
                    aria-selected={isActive}
                    onClick={() => setFilterDate(label)}
                    className={`
                      flex-1 px-2 py-1.5 rounded-lg text-xs font-bold whitespace-nowrap transition-all focus:ring-2 focus:ring-blue-500 focus:outline-none flex items-center justify-center gap-1
                      ${isActive
                        ? "bg-green-600 text-white shadow-md"
                        : "bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700"
                      }
                    `}
                  >
                    <span>{icon}</span> {label === "FDS" ? "Fim de semana" : label === "Semana" ? "7 dias" : label}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Lista Scrollável */}
          <div className="flex-1 overflow-y-auto p-4 bg-gray-50 dark:bg-gray-950/50 transition-colors scroll-smooth">
            {loading ? (
              // Skeleton loading
              Array.from({ length: 5 }).map((_, i) => (
                <div key={i} className="bg-white dark:bg-gray-800 rounded-xl p-4 mb-3 animate-pulse">
                  <div className="flex justify-between items-start mb-3">
                    <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-3/4" />
                    <div className="h-5 w-5 bg-gray-200 dark:bg-gray-700 rounded-full" />
                  </div>
                  <div className="h-3 bg-gray-200 dark:bg-gray-700 rounded w-1/2 mb-2" />
                  <div className="h-3 bg-gray-200 dark:bg-gray-700 rounded w-2/3" />
                </div>
              ))
            ) : (
              <>
                {activeTab === 'favoritos' && (
                  <div className="flex items-center gap-2 mb-3">
                    <span className="text-lg">❤️</span>
                    <h2 className="text-sm font-bold text-gray-700 dark:text-gray-300">Meus Favoritos ({userFavorites.length})</h2>
                  </div>
                )}
                {(() => {
                  const displayEvents = activeTab === 'favoritos' 
                    ? processedEvents.filter(e => userFavorites.includes(e.id))
                    : processedEvents;
                  
                  if (displayEvents.length === 0) {
                    return (
                      <div className="flex flex-col items-center justify-center h-40 text-center text-gray-400 dark:text-gray-500 mt-10">
                        <span className="text-3xl mb-2">{activeTab === 'favoritos' ? '💔' : '🤔'}</span>
                        <p className="font-medium">
                          {activeTab === 'favoritos' 
                            ? 'Ainda sem favoritos. Toca no ❤️ num evento para guardar!' 
                            : 'Nenhum evento encontrado.'}
                        </p>
                      </div>
                    );
                  }
                  return displayEvents.map((event) => (
                    <EventCard
                      key={event.id}
                      event={event}
                      distance={event.distance || null}
                      isFavorite={userFavorites.includes(event.id)}
                      onSelect={handleSelectEvent}
                      onToggleFavorite={handleToggleFavorite}
                    />
                  ));
                })()}
              </>
            )}
          </div>
        </div>

        {/* COLUNA DIREITA: MAPA */}
        <div className={`
            w-full md:w-2/3 lg:w-3/4 h-full bg-gray-200 dark:bg-gray-800 relative transition-colors
            ${activeTab === 'mapa' ? 'block' : 'hidden md:block'}
        `}>
          <MapComponent 
            events={processedEvents} 
            negocios={negocios}
            userLocation={userLocation}
            onSelectEvent={handleSelectEvent}
          />
          
          {/* Floating Action Button (Mobile) - Geolocalização Rápida */}
          <button 
             onClick={() => handleLocationChange("gps")}
             aria-label="Usar minha localização GPS"
             className="absolute bottom-24 right-6 z-[1000] bg-white dark:bg-gray-800 text-blue-600 dark:text-blue-400 p-4 rounded-full shadow-xl hover:bg-gray-50 dark:hover:bg-gray-700 md:hidden focus:ring-2 focus:ring-blue-500 focus:outline-none transition-transform active:scale-95"
          >
             <span className="text-xl">🎯</span>
          </button>
        </div>

      </main>

      {/* MOBILE TABS (Navegação Inferior) */}
      <nav className="md:hidden bg-white dark:bg-gray-900 border-t border-gray-200 dark:border-gray-800 flex justify-around p-1.5 pb-safe z-30 transition-colors">
        <button 
            onClick={() => setActiveTab('lista')}
            className={`flex flex-col items-center p-1.5 rounded-lg w-full transition-colors ${activeTab === 'lista' ? 'text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/20' : 'text-gray-400 dark:text-gray-500'}`}
        >
            <span className="text-lg mb-0.5">📅</span>
            <span className="text-[10px] font-bold">Lista</span>
        </button>
        <button 
            onClick={() => setActiveTab('mapa')}
            className={`flex flex-col items-center p-1.5 rounded-lg w-full transition-colors ${activeTab === 'mapa' ? 'text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/20' : 'text-gray-400 dark:text-gray-500'}`}
        >
            <span className="text-lg mb-0.5">🗺️</span>
            <span className="text-[10px] font-bold">Mapa</span>
        </button>
        <button
            onClick={() => setActiveTab('favoritos')}
            className={`flex flex-col items-center p-1.5 rounded-lg w-full transition-colors relative ${activeTab === 'favoritos' ? 'text-pink-600 dark:text-pink-400 bg-pink-50 dark:bg-pink-900/20' : 'text-gray-400 dark:text-gray-500'}`}
        >
            <span className="text-lg mb-0.5">❤️</span>
            <span className="text-[10px] font-bold">Favoritos</span>
            {userFavorites.length > 0 && (
              <span className="absolute top-0.5 right-1/4 bg-pink-500 text-white text-[8px] font-bold min-w-[14px] h-[14px] flex items-center justify-center rounded-full">{userFavorites.length}</span>
            )}
        </button>
        <Link
            href="/submit"
            className="flex flex-col items-center p-1.5 rounded-lg w-full transition-colors text-gray-400 dark:text-gray-500 active:text-green-600 dark:active:text-green-400"
        >
            <span className="text-lg mb-0.5">➕</span>
            <span className="text-[10px] font-bold">Submeter</span>
        </Link>
      </nav>

      {/* Event Detail Modal */}
      {selectedEvent && (
        <EventDetailModal
          event={selectedEvent}
          distance={selectedEvent.distance || null}
          userLocation={userLocation}
          userId={userId}
          isFavorite={userFavorites.includes(selectedEvent.id)}
          allEvents={processedEvents}
          onClose={() => setSelectedEvent(null)}
          onToggleFavorite={() => handleToggleFavorite(selectedEvent.id)}
          onShowOnMap={handleShowOnMap}
          onSelectEvent={handleSelectEvent}
        />
      )}

      {/* Chatbot Groq */}
      <ChatWidget />
    </div>
  );
}
