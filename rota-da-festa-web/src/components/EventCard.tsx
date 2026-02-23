"use client";

interface EventCardProps {
  event: any;
  distance: number | null;
  isFavorite: boolean;
  onSelect: (event: any) => void;
  onToggleFavorite: (eventId: number) => void;
}

export default function EventCard({ event, distance, isFavorite, onSelect, onToggleFavorite }: EventCardProps) {

  const isFutebol = event.tipo === "Futebol";
  const isAdiado = event.status === "adiado";

  const hoje = new Date().toISOString().split("T")[0];
  const amanha = new Date(Date.now() + 86400000).toISOString().split("T")[0];
  const isHoje = event.data === hoje;
  const isAmanha = event.data === amanha;

  const typeConfig: Record<string, { icon: string; bg: string; text: string }> = {
    "Futebol": { icon: "⚽", bg: "bg-green-100 dark:bg-green-900", text: "text-green-800 dark:text-green-100" },
    "Festa": { icon: "🎪", bg: "bg-red-100 dark:bg-red-900", text: "text-red-800 dark:text-red-100" },
    "Concerto": { icon: "🎵", bg: "bg-purple-100 dark:bg-purple-900", text: "text-purple-800 dark:text-purple-100" },
    "Feira": { icon: "🍖", bg: "bg-amber-100 dark:bg-amber-900", text: "text-amber-800 dark:text-amber-100" },
    "Cultura": { icon: "🎭", bg: "bg-pink-100 dark:bg-pink-900", text: "text-pink-800 dark:text-pink-100" },
    "Desporto": { icon: "🏃", bg: "bg-cyan-100 dark:bg-cyan-900", text: "text-cyan-800 dark:text-cyan-100" },
    "Tradição": { icon: "🔥", bg: "bg-orange-100 dark:bg-orange-900", text: "text-orange-800 dark:text-orange-100" },
  };
  const tc = typeConfig[event.tipo] || { icon: "📌", bg: "bg-gray-100 dark:bg-gray-700", text: "text-gray-800 dark:text-gray-100" };
  const borderColor = isAdiado ? "border-orange-400" : isFavorite ? "border-yellow-400" : isFutebol ? "border-green-500" : "border-red-500";

  return (
    <div
      onClick={() => onSelect(event)}
      className={`
      relative group bg-white dark:bg-gray-800 rounded-xl shadow-sm border-l-4 p-4 mb-3 cursor-pointer
      transition-all hover:shadow-lg hover:scale-[1.01] 
      ${isAdiado ? "opacity-60" : ""}
      ${borderColor}
    `}>
      <div className="flex justify-between items-start">
        <div className="flex-1">
          {/* Badge Tipo + Escalão + Status */}
          <div className="flex items-center gap-2 mb-2 flex-wrap">
            {isAdiado && (
              <span className="text-[10px] uppercase font-bold px-2 py-0.5 rounded-full tracking-wider bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-100 animate-pulse">
                ⚠️ Adiado
              </span>
            )}
            {isHoje && !isAdiado && (
              <span className="text-[10px] uppercase font-bold px-2 py-0.5 rounded-full tracking-wider bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-100 animate-pulse">
                🔴 Hoje
              </span>
            )}
            {isAmanha && !isAdiado && (
              <span className="text-[10px] uppercase font-bold px-2 py-0.5 rounded-full tracking-wider bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-100">
                Amanhã
              </span>
            )}
            <span className={`
              text-[10px] uppercase font-bold px-2 py-0.5 rounded-full tracking-wider
              ${tc.bg} ${tc.text}
            `}>
              {tc.icon} {event.tipo}
            </span>
            {isFutebol && event.escalao && (
              <span className={`
                text-[10px] font-bold px-2 py-0.5 rounded-full tracking-wider
                ${event.escalao === "Seniores"
                  ? "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-100"
                  : "bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-100"
                }
              `}>
                {event.escalao}
              </span>
            )}
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
          <div className="flex justify-between items-center text-sm bg-gray-50 dark:bg-gray-800 p-2.5 rounded-lg border border-gray-100 dark:border-gray-700">
            <span className="text-gray-700 dark:text-gray-300 font-semibold">📅 {event.data}</span>
            <span className="text-gray-500 dark:text-gray-400">🕒 {event.hora}</span>
            <span className="font-bold text-gray-900 dark:text-white px-2 py-0.5 bg-white dark:bg-gray-700 rounded shadow-sm">
              {event.preco}
              {event.preco?.includes("estimado") && (
                <span className="text-[8px] text-amber-600 dark:text-amber-400 ml-0.5" title="Preço médio estimado">⚠</span>
              )}
            </span>
          </div>
        </div>

        {/* Botão Favorito */}
        <button
          onClick={(e) => { e.stopPropagation(); onToggleFavorite(event.id); }}
          aria-label={isFavorite ? "Remover dos favoritos" : "Adicionar aos favoritos"}
          className={`
            ml-3 p-2.5 rounded-full transition-colors focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 focus:outline-none
            ${isFavorite 
              ? "text-red-500 bg-red-50 dark:bg-red-900/40" 
              : "text-gray-300 dark:text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-700"
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
