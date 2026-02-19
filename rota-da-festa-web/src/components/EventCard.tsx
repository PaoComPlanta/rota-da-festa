"use client";

import { useState } from "react";
import { supabase } from "@/utils/supabase/client";

interface EventCardProps {
  event: any;
  distance: number | null;
  userId: string | null;
  isFavoriteInicial: boolean;
}

export default function EventCard({ event, distance, userId, isFavoriteInicial }: EventCardProps) {
  const [isFavorite, setIsFavorite] = useState(isFavoriteInicial);
  const [loading, setLoading] = useState(false);

  const toggleFavorite = async () => {
    if (!userId) return alert("Faz login para guardar favoritos!");
    
    setLoading(true);
    
    if (isFavorite) {
      // Remover
      const { error } = await supabase
        .from("favoritos")
        .delete()
        .match({ user_id: userId, evento_id: event.id });
      if (!error) setIsFavorite(false);
    } else {
      // Adicionar
      const { error } = await supabase
        .from("favoritos")
        .insert({ user_id: userId, evento_id: event.id });
      if (!error) setIsFavorite(true);
    }
    
    setLoading(false);
  };

  const isFutebol = event.tipo === "Futebol";

  return (
    <div className={`
      relative group bg-white dark:bg-gray-800 rounded-xl shadow-sm border-l-4 p-4 mb-3 
      transition-all hover:shadow-lg hover:scale-[1.01] 
      ${isFutebol ? "border-green-500" : "border-red-500"}
      ${isFavorite ? "border-yellow-400" : ""}
    `}>
      <div className="flex justify-between items-start">
        <div className="flex-1">
          {/* Badge Tipo */}
          <div className="flex items-center gap-2 mb-2">
            <span className={`
              text-[10px] uppercase font-bold px-2 py-0.5 rounded-full tracking-wider
              ${isFutebol 
                ? "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-100" 
                : "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-100"
              }
            `}>
              {event.tipo}
            </span>
            {distance !== null && (
              <span className="text-xs text-gray-500 dark:text-gray-400 font-medium">
                {distance.toFixed(1)} km
              </span>
            )}
          </div>
          
          {/* Nome */}
          <h3 className="font-bold text-gray-900 dark:text-gray-100 text-lg leading-tight mb-1 line-clamp-2">
            {event.nome}
          </h3>
          
          {/* Local */}
          <p className="text-sm text-gray-600 dark:text-gray-400 mb-3 flex items-center gap-1 font-medium">
            📍 {event.local}
          </p>

          {/* Metadata Grid */}
          <div className="flex justify-between items-center text-sm bg-gray-50 dark:bg-gray-700/50 p-2.5 rounded-lg border border-gray-100 dark:border-gray-700">
            <span className="text-gray-700 dark:text-gray-300 font-semibold">📅 {event.data}</span>
            <span className="text-gray-500 dark:text-gray-400">🕒 {event.hora}</span>
            <span className="font-bold text-gray-900 dark:text-white px-2 py-0.5 bg-white dark:bg-gray-600 rounded shadow-sm">
              {event.preco}
            </span>
          </div>
        </div>

        {/* Botão Favorito */}
        <button
          onClick={toggleFavorite}
          disabled={loading}
          aria-label={isFavorite ? "Remover dos favoritos" : "Adicionar aos favoritos"}
          className={`
            ml-3 p-2.5 rounded-full transition-colors focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 focus:outline-none
            ${isFavorite 
              ? "text-red-500 bg-red-50 dark:bg-red-900/30" 
              : "text-gray-300 dark:text-gray-600 hover:bg-gray-100 dark:hover:bg-gray-700"
            }
          `}
        >
          <svg xmlns="http://www.w3.org/2000/svg" fill={isFavorite ? "currentColor" : "none"} viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" className="w-6 h-6">
            <path strokeLinecap="round" strokeLinejoin="round" d="M21 8.25c0-2.485-2.099-4.5-4.688-4.5-1.935 0-3.597 1.126-4.312 2.733-.715-1.607-2.377-2.733-4.313-2.733C5.1 3.75 3 5.765 3 8.25c0 7.22 9 12 9 12s9-4.78 9-12z" />
          </svg>
        </button>
      </div>
    </div>
  );
}
