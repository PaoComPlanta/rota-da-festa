import { createClient } from "@supabase/supabase-js";
import { Metadata } from "next";
import { notFound } from "next/navigation";
import Link from "next/link";

const DISTRICT_CENTROIDS: Record<string, { lat: number; lon: number; name: string }> = {
  "braga": { lat: 41.5503, lon: -8.4270, name: "Braga" },
  "porto": { lat: 41.1496, lon: -8.6109, name: "Porto" },
  "aveiro": { lat: 40.6405, lon: -8.6538, name: "Aveiro" },
  "lisboa": { lat: 38.7223, lon: -9.1393, name: "Lisboa" },
  "leiria": { lat: 39.7437, lon: -8.8070, name: "Leiria" },
  "coimbra": { lat: 40.2109, lon: -8.4377, name: "Coimbra" },
  "viseu": { lat: 40.6610, lon: -7.9097, name: "Viseu" },
  "setubal": { lat: 38.5244, lon: -8.8882, name: "Setúbal" },
  "santarem": { lat: 39.2369, lon: -8.6850, name: "Santarém" },
  "beja": { lat: 38.0150, lon: -7.8653, name: "Beja" },
  "faro": { lat: 37.0194, lon: -7.9304, name: "Faro" },
  "evora": { lat: 38.5667, lon: -7.9000, name: "Évora" },
  "braganca": { lat: 41.8063, lon: -6.7572, name: "Bragança" },
  "castelo-branco": { lat: 39.8228, lon: -7.4906, name: "Castelo Branco" },
  "guarda": { lat: 40.5373, lon: -7.2676, name: "Guarda" },
  "viana-do-castelo": { lat: 41.6936, lon: -8.8319, name: "Viana do Castelo" },
  "vila-real": { lat: 41.2959, lon: -7.7464, name: "Vila Real" },
  "portalegre": { lat: 39.2967, lon: -7.4317, name: "Portalegre" },
  "madeira": { lat: 32.6669, lon: -16.9241, name: "Madeira" },
  "acores": { lat: 37.7483, lon: -25.6666, name: "Açores" },
};

const DISTRICT_RADIUS_KM = 60;

function haversineKm(lat1: number, lon1: number, lat2: number, lon2: number) {
  const R = 6371;
  const dLat = ((lat2 - lat1) * Math.PI) / 180;
  const dLon = ((lon2 - lon1) * Math.PI) / 180;
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos((lat1 * Math.PI) / 180) * Math.cos((lat2 * Math.PI) / 180) * Math.sin(dLon / 2) ** 2;
  return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

function getSupabase() {
  return createClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
  );
}

type Props = { params: Promise<{ distrito: string }> };

export async function generateStaticParams() {
  return Object.keys(DISTRICT_CENTROIDS).map((distrito) => ({ distrito }));
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { distrito } = await params;
  const info = DISTRICT_CENTROIDS[distrito];
  if (!info) return { title: "Distrito não encontrado" };

  return {
    title: `Jogos de Futebol em ${info.name} — Rota da Festa`,
    description: `Todos os jogos de futebol este fim de semana em ${info.name}. Seniores, formação, distrital. No mapa. Grátis.`,
    openGraph: {
      title: `Jogos em ${info.name} — Rota da Festa`,
      description: `Descobre todos os jogos de futebol perto de ${info.name} este fim de semana.`,
      type: "website",
      locale: "pt_PT",
    },
  };
}

async function getEventsByDistrict(distrito: string) {
  const info = DISTRICT_CENTROIDS[distrito];
  if (!info) return null;

  const supabase = getSupabase();
  const { data, error } = await supabase
    .from("eventos")
    .select("*")
    .in("status", ["aprovado", "adiado"])
    .order("data", { ascending: true });

  if (error || !data) return [];

  return data.filter((ev: any) =>
    ev.latitude && ev.longitude &&
    haversineKm(info.lat, info.lon, ev.latitude, ev.longitude) <= DISTRICT_RADIUS_KM
  );
}

export const revalidate = 3600; // ISR: revalidar a cada hora

export default async function DistritoPage({ params }: Props) {
  const { distrito } = await params;
  const info = DISTRICT_CENTROIDS[distrito];
  if (!info) notFound();

  const events = await getEventsByDistrict(distrito);

  const hoje = new Date().toISOString().split("T")[0];

  // JSON-LD structured data
  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "ItemList",
    name: `Jogos de Futebol em ${info.name}`,
    description: `Lista de jogos de futebol no distrito de ${info.name}`,
    numberOfItems: events?.length || 0,
    itemListElement: events?.slice(0, 20).map((ev: any, i: number) => ({
      "@type": "ListItem",
      position: i + 1,
      item: {
        "@type": "SportsEvent",
        name: ev.nome,
        startDate: `${ev.data}T${ev.hora || "15:00"}`,
        location: {
          "@type": "Place",
          name: ev.local,
          geo: { "@type": "GeoCoordinates", latitude: ev.latitude, longitude: ev.longitude },
        },
      },
    })),
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950 text-gray-900 dark:text-gray-100">
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />

      {/* Header */}
      <header className="bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-800 px-4 py-4 shadow-sm">
        <div className="max-w-3xl mx-auto flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2 hover:opacity-80 transition-opacity">
            <span className="text-2xl">🎉</span>
            <span className="text-lg font-extrabold bg-gradient-to-r from-green-600 to-blue-600 bg-clip-text text-transparent">
              Rota da Festa
            </span>
          </Link>
          <Link
            href="/"
            className="text-sm font-bold text-white bg-black dark:bg-white dark:text-black px-4 py-2 rounded-lg hover:opacity-90 transition-opacity"
          >
            Ver Mapa
          </Link>
        </div>
      </header>

      {/* Content */}
      <main className="max-w-3xl mx-auto px-4 py-8">
        <h1 className="text-3xl font-extrabold mb-2">
          ⚽ Jogos em {info.name}
        </h1>
        <p className="text-gray-500 dark:text-gray-400 mb-6">
          {events && events.length > 0
            ? `${events.length} jogos encontrados no distrito de ${info.name}.`
            : `Sem jogos agendados de momento em ${info.name}.`}
        </p>

        {/* District quick nav */}
        <div className="flex flex-wrap gap-2 mb-8">
          {Object.entries(DISTRICT_CENTROIDS).map(([slug, d]) => (
            <Link
              key={slug}
              href={`/jogos/${slug}`}
              className={`px-3 py-1 rounded-full text-xs font-bold transition-colors ${
                slug === distrito
                  ? "bg-green-600 text-white"
                  : "bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700"
              }`}
            >
              {d.name}
            </Link>
          ))}
        </div>

        {/* Events list */}
        {events && events.length > 0 ? (
          <div className="space-y-4">
            {events.map((ev: any) => {
              const isHoje = ev.data === hoje;
              const isAdiado = ev.status === "adiado";
              return (
                <article
                  key={ev.id}
                  className={`bg-white dark:bg-gray-900 rounded-xl shadow-sm border-l-4 p-4 ${
                    isAdiado ? "border-orange-400 opacity-60" : "border-green-500"
                  }`}
                >
                  <div className="flex items-center gap-2 mb-2 flex-wrap">
                    {isAdiado && (
                      <span className="text-[10px] uppercase font-bold px-2 py-0.5 rounded-full bg-orange-100 text-orange-800">
                        ⚠️ Adiado
                      </span>
                    )}
                    {isHoje && !isAdiado && (
                      <span className="text-[10px] uppercase font-bold px-2 py-0.5 rounded-full bg-red-100 text-red-700 animate-pulse">
                        🔴 Hoje
                      </span>
                    )}
                    {ev.escalao && (
                      <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-blue-100 text-blue-800">
                        {ev.escalao}
                      </span>
                    )}
                    {ev.categoria && (
                      <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400">
                        {ev.categoria}
                      </span>
                    )}
                  </div>
                  <h2 className="font-bold text-lg mb-1">{ev.nome}</h2>
                  <p className="text-sm text-gray-500 dark:text-gray-400 mb-2">📍 {ev.local}</p>
                  <div className="flex gap-4 text-sm text-gray-600 dark:text-gray-300">
                    <span>📅 {ev.data}</span>
                    <span>🕒 {ev.hora}</span>
                    {ev.preco && <span className="font-bold">{ev.preco}</span>}
                  </div>
                </article>
              );
            })}
          </div>
        ) : (
          <div className="text-center py-16 text-gray-400">
            <span className="text-4xl block mb-3">🤔</span>
            <p className="font-medium">Sem jogos agendados em {info.name}.</p>
            <p className="text-sm mt-1">Os jogos são atualizados diariamente.</p>
          </div>
        )}

        {/* CTA */}
        <div className="mt-12 text-center bg-gradient-to-r from-green-50 to-blue-50 dark:from-green-950/30 dark:to-blue-950/30 rounded-2xl p-8">
          <h2 className="text-xl font-bold mb-2">🗺️ Ver no Mapa</h2>
          <p className="text-gray-500 dark:text-gray-400 mb-4">
            Visualiza todos os jogos num mapa interativo com direções GPS.
          </p>
          <Link
            href="/"
            className="inline-block bg-green-600 text-white font-bold px-6 py-3 rounded-xl hover:bg-green-700 transition-colors"
          >
            Abrir Mapa Interativo
          </Link>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-gray-200 dark:border-gray-800 mt-16 py-8 text-center text-sm text-gray-400 dark:text-gray-500">
        <p>© {new Date().getFullYear()} Rota da Festa — Todos os jogos e festas de Portugal. Grátis.</p>
      </footer>
    </div>
  );
}
