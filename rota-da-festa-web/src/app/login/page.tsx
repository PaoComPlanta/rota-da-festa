"use client";

import { supabase } from "@/utils/supabase/client";

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
    <div className="h-screen w-screen flex flex-col items-center justify-center bg-gray-50 p-6">
      <div className="w-full max-w-sm bg-white rounded-2xl shadow-xl p-8 text-center">
        <div className="mb-6">
          <span className="text-4xl">🎉</span>
        </div>
        
        <h1 className="text-2xl font-bold text-gray-900 mb-2">Rota da Festa</h1>
        <p className="text-gray-500 mb-8">
          Entra para guardares os teus jogos e romarias favoritas.
        </p>

        <button
          onClick={handleLogin}
          className="w-full flex items-center justify-center gap-3 bg-white border border-gray-300 text-gray-700 font-medium py-3 px-4 rounded-xl hover:bg-gray-50 transition-colors"
        >
          <img 
            src="https://www.svgrepo.com/show/475656/google-color.svg" 
            alt="Google" 
            className="w-5 h-5"
          />
          Continuar com Google
        </button>
        
        <p className="mt-6 text-xs text-gray-400">
          Ao continuar, aceitas os Termos de Serviço da festa rija.
        </p>
      </div>
    </div>
  );
}
