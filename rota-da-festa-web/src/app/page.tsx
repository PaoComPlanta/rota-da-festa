"use client";

import { useEffect, useState, useMemo, useCallback } from "react";
import dynamic from "next/dynamic";
import { supabase } from "@/utils/supabase/client";
import EventCard from "@/components/EventCard";
import EventDetailModal from "@/components/EventDetailModal";
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

export default function Home() {
  const { theme, toggleTheme } = useTheme();
  
  // Coordenadas de Braga por defeito
  const DEFAULT_BRAGA = { lat: 41.5503, lng: -8.4270 };
  
  const [events, setEvents] = useState<any[]>([]);
  const [userLocation, setUserLocation] = useState<{ lat: number; lng: number } | null>(DEFAULT_BRAGA);
  const [searchTerm, setSearchTerm] = useState("");
  const [filterType, setFilterType] = useState("Todos");
  const [filterEscalao, setFilterEscalao] = useState("Todos");
  const [activeTab, setActiveTab] = useState<"lista" | "mapa">("lista");
  const [userId, setUserId] = useState<string | null>(null);
  const [userFavorites, setUserFavorites] = useState<number[]>(() => {
    if (typeof window !== "undefined") {
      try {
        return JSON.parse(localStorage.getItem("rotadafesta_favs") || "[]");
      } catch { return []; }
    }
    return [];
  });
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
    } else if (val === "braga") {
      setUserLocation(DEFAULT_BRAGA);
    } else if (val === "porto") {
      setUserLocation({ lat: 41.1579, lng: -8.6291 });
    } else if (val === "aveiro") {
      setUserLocation({ lat: 40.6405, lng: -8.6538 });
    }
  };

  async function fetchEvents() {
    const { data, error } = await supabase.from("eventos").select("*");
    if (!error && data) setEvents(data);
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

  const processedEvents = useMemo(() => {
    let filtered = events.filter((ev) => {
      const matchesSearch = ev.nome.toLowerCase().includes(searchTerm.toLowerCase());
      const matchesType = filterType === "Todos" || ev.tipo === filterType;
      const matchesEscalao = filterEscalao === "Todos" || ev.escalao === filterEscalao;
      // Esconder eventos pendentes (não aprovados nem adiados)
      const isVisible = ev.status === "aprovado" || ev.status === "adiado";
      return matchesSearch && matchesType && matchesEscalao && isVisible;
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
  }, [events, userLocation, searchTerm, filterType, filterEscalao]);

  return (
    <div className="h-screen w-screen flex flex-col overflow-hidden bg-gray-50 dark:bg-gray-950 text-gray-900 dark:text-gray-100 transition-colors duration-300">
      
      {/* HEADER ACESSÍVEL */}
      <header className="bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-800 px-4 py-3 flex justify-between items-center z-20 shadow-sm transition-colors">
        <div className="flex items-center gap-2">
          <span className="text-2xl" role="img" aria-label="Logo">🎉</span>
          <h1 className="text-xl font-extrabold tracking-tight bg-gradient-to-r from-green-600 to-blue-600 bg-clip-text text-transparent hidden sm:block">
            Rota da Festa
          </h1>
        </div>

        <div className="flex items-center gap-3">
          {/* Seletor de Cidade */}
          <select
            value={citySelection}
            onChange={(e) => handleLocationChange(e.target.value)}
            className="bg-gray-100 dark:bg-gray-800 text-gray-800 dark:text-gray-200 text-sm rounded-lg px-3 py-2 border-none focus:ring-2 focus:ring-blue-500 outline-none font-medium cursor-pointer transition-colors"
            aria-label="Escolher localização"
          >
            <option value="braga">📍 Braga</option>
            <option value="porto">📍 Porto</option>
            <option value="aveiro">📍 Aveiro</option>
            <option value="gps">🎯 Minha Localização</option>
          </select>

          {/* Botão de Tema */}
          <button
            onClick={toggleTheme}
            className="p-2 rounded-full bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors focus:ring-2 focus:ring-blue-500 focus:outline-none"
            aria-label={theme === "light" ? "Mudar para modo escuro" : "Mudar para modo claro"}
          >
            {theme === "light" ? "🌙" : "☀️"}
          </button>

          {/* Login Status */}
          {userId ? (
             <div className="hidden sm:block text-xs font-semibold text-green-600 dark:text-green-400 bg-green-100 dark:bg-green-900/30 px-2 py-1 rounded">
               Logado
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
              {["Todos", "Futebol", "Festa/Romaria"].map((type) => {
                const isActive = filterType === type;
                return (
                  <button
                    key={type}
                    role="tab"
                    aria-selected={isActive}
                    onClick={() => { setFilterType(type); if (type !== "Futebol") setFilterEscalao("Todos"); }}
                    className={`
                      px-4 py-1.5 rounded-full text-xs font-bold whitespace-nowrap transition-all focus:ring-2 focus:ring-blue-500 focus:outline-none
                      ${isActive 
                        ? "bg-black dark:bg-white text-white dark:text-black shadow-md" 
                        : "bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700"
                      }
                    `}
                  >
                    {type}
                  </button>
                );
              })}
            </div>

            {/* Filtro de Escalão (só visível para Futebol ou Todos) */}
            {filterType !== "Festa/Romaria" && (
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
          </div>

          {/* Lista Scrollável */}
          <div className="flex-1 overflow-y-auto p-4 bg-gray-50 dark:bg-gray-950/50 transition-colors scroll-smooth">
            {processedEvents.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-40 text-center text-gray-400 dark:text-gray-500 mt-10">
                    <span className="text-3xl mb-2">🤔</span>
                    <p className="font-medium">Nenhum evento encontrado.</p>
                </div>
            ) : (
                processedEvents.map((event) => (
                <EventCard
                    key={event.id}
                    event={event}
                    distance={event.distance || null}
                    isFavorite={userFavorites.includes(event.id)}
                    onSelect={handleSelectEvent}
                    onToggleFavorite={handleToggleFavorite}
                />
                ))
            )}
          </div>
        </div>

        {/* COLUNA DIREITA: MAPA */}
        <div className={`
            w-full md:w-2/3 lg:w-3/4 h-full bg-gray-200 dark:bg-gray-800 relative transition-colors
            ${activeTab === 'lista' ? 'hidden md:block' : 'block'}
        `}>
          <MapComponent 
            events={processedEvents} 
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
      <nav className="md:hidden bg-white dark:bg-gray-900 border-t border-gray-200 dark:border-gray-800 flex justify-around p-2 pb-safe z-30 transition-colors">
        <button 
            onClick={() => setActiveTab('lista')}
            className={`flex flex-col items-center p-2 rounded-lg w-full transition-colors ${activeTab === 'lista' ? 'text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/20' : 'text-gray-400 dark:text-gray-500'}`}
        >
            <span className="text-xl mb-1">📅</span>
            <span className="text-xs font-bold">Lista</span>
        </button>
        <button 
            onClick={() => setActiveTab('mapa')}
            className={`flex flex-col items-center p-2 rounded-lg w-full transition-colors ${activeTab === 'mapa' ? 'text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/20' : 'text-gray-400 dark:text-gray-500'}`}
        >
            <span className="text-xl mb-1">🗺️</span>
            <span className="text-xs font-bold">Mapa</span>
        </button>
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
    </div>
  );
}
