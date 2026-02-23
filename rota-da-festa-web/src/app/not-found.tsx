import Link from "next/link";

export default function NotFound() {
  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950 flex flex-col items-center justify-center px-4 text-center">
      <span className="text-7xl mb-4">🗺️</span>
      <h1 className="text-4xl font-extrabold text-gray-900 dark:text-white mb-2">Página não encontrada</h1>
      <p className="text-gray-500 dark:text-gray-400 mb-8 max-w-md">
        Parece que te perdeste! Não encontrámos o que procuras, mas temos muitos jogos e festas à tua espera.
      </p>
      <div className="flex gap-3">
        <Link
          href="/"
          className="bg-green-600 text-white font-bold px-6 py-3 rounded-xl hover:bg-green-700 transition-colors"
        >
          🎉 Ver Mapa
        </Link>
        <Link
          href="/submit"
          className="bg-gray-200 dark:bg-gray-800 text-gray-800 dark:text-gray-200 font-bold px-6 py-3 rounded-xl hover:bg-gray-300 dark:hover:bg-gray-700 transition-colors"
        >
          ➕ Submeter Evento
        </Link>
      </div>
    </div>
  );
}
