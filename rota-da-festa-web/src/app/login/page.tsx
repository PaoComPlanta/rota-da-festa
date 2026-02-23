"use client";

import { supabase } from "@/utils/supabase/client";
import Link from "next/link";

export default function Login() {
  const handleLogin = async () => {
    await supabase.auth.signInWithOAuth({
      provider: "google",
      options: {
        redirectTo: `${window.location.origin}/`,
      },
    });
  };

  return (
    <div className="h-screen w-screen flex flex-col items-center justify-center bg-gray-50 dark:bg-gray-950 p-6 transition-colors">
      <div className="w-full max-w-sm bg-white dark:bg-gray-900 rounded-2xl shadow-xl p-8 text-center border border-gray-100 dark:border-gray-800">
        <div className="mb-6">
          <span className="text-4xl">🎉</span>
        </div>
        
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">Rota da Festa</h1>
        <p className="text-gray-500 dark:text-gray-400 mb-8">
          Entra para guardares os teus jogos e festas favoritas.
        </p>

        <button
          onClick={handleLogin}
          className="w-full flex items-center justify-center gap-3 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-700 text-gray-700 dark:text-gray-200 font-medium py-3 px-4 rounded-xl hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
        >
          <img 
            src="https://www.svgrepo.com/show/475656/google-color.svg" 
            alt="Google" 
            className="w-5 h-5"
          />
          Continuar com Google
        </button>
        
        <Link href="/" className="block mt-6 text-sm text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300 transition-colors">
          ← Voltar ao mapa
        </Link>
      </div>
    </div>
  );
}
