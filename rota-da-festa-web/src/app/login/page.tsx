"use client";

import { useState } from "react";
import { supabase } from "@/utils/supabase/client";
import Link from "next/link";

export default function Login() {
  const [mode, setMode] = useState<"login" | "signup">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<{ text: string; type: "error" | "success" } | null>(null);

  const handleGoogle = async () => {
    await supabase.auth.signInWithOAuth({
      provider: "google",
      options: { redirectTo: `${window.location.origin}/` },
    });
  };

  const handleEmailAuth = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setMessage(null);

    if (password.length < 8) {
      setMessage({ text: "A password deve ter pelo menos 8 caracteres.", type: "error" });
      setLoading(false);
      return;
    }

    if (mode === "signup") {
      const { error } = await supabase.auth.signUp({
        email,
        password,
        options: { emailRedirectTo: `${window.location.origin}/` },
      });
      if (error) {
        setMessage({ text: error.message, type: "error" });
      } else {
        setMessage({ text: "Verifica o teu email para confirmar a conta!", type: "success" });
      }
    } else {
      const { error } = await supabase.auth.signInWithPassword({ email, password });
      if (error) {
        setMessage({ text: "Email ou password incorretos.", type: "error" });
      } else {
        window.location.href = "/";
      }
    }
    setLoading(false);
  };

  return (
    <div className="h-screen w-screen flex flex-col items-center justify-center bg-gray-50 dark:bg-gray-950 p-6 transition-colors">
      <div className="w-full max-w-sm bg-white dark:bg-gray-900 rounded-2xl shadow-xl p-8 text-center border border-gray-100 dark:border-gray-800">
        <div className="mb-4">
          <span className="text-4xl">🎉</span>
        </div>
        
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-1">Rota da Festa</h1>
        <p className="text-gray-500 dark:text-gray-400 mb-6 text-sm">
          {mode === "login" ? "Entra na tua conta" : "Cria a tua conta"}
        </p>

        {/* Google OAuth */}
        <button
          onClick={handleGoogle}
          className="w-full flex items-center justify-center gap-3 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-700 text-gray-700 dark:text-gray-200 font-medium py-3 px-4 rounded-xl hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
        >
          <img src="https://www.svgrepo.com/show/475656/google-color.svg" alt="Google" className="w-5 h-5" />
          Continuar com Google
        </button>

        {/* Divider */}
        <div className="flex items-center gap-3 my-5">
          <div className="flex-1 h-px bg-gray-200 dark:bg-gray-700" />
          <span className="text-xs text-gray-400 dark:text-gray-500 font-medium">ou</span>
          <div className="flex-1 h-px bg-gray-200 dark:bg-gray-700" />
        </div>

        {/* Email/Password Form */}
        <form onSubmit={handleEmailAuth} className="space-y-3 text-left">
          <div>
            <input
              type="email"
              required
              placeholder="Email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full bg-gray-100 dark:bg-gray-800 text-gray-900 dark:text-white border-none rounded-lg px-4 py-2.5 focus:ring-2 focus:ring-blue-500 outline-none transition-colors placeholder-gray-400 dark:placeholder-gray-500 text-sm"
            />
          </div>
          <div>
            <input
              type="password"
              required
              minLength={8}
              placeholder="Password (mín. 8 caracteres)"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full bg-gray-100 dark:bg-gray-800 text-gray-900 dark:text-white border-none rounded-lg px-4 py-2.5 focus:ring-2 focus:ring-blue-500 outline-none transition-colors placeholder-gray-400 dark:placeholder-gray-500 text-sm"
            />
          </div>

          {message && (
            <p className={`text-xs font-medium px-1 ${message.type === "error" ? "text-red-500" : "text-green-500"}`}>
              {message.text}
            </p>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-green-600 text-white font-bold py-2.5 rounded-xl hover:bg-green-700 transition-colors disabled:opacity-60 text-sm"
          >
            {loading ? "A processar..." : mode === "login" ? "Entrar" : "Criar Conta"}
          </button>
        </form>

        {/* Toggle mode */}
        <p className="mt-5 text-sm text-gray-500 dark:text-gray-400">
          {mode === "login" ? "Não tens conta?" : "Já tens conta?"}{" "}
          <button
            onClick={() => { setMode(mode === "login" ? "signup" : "login"); setMessage(null); }}
            className="text-blue-600 dark:text-blue-400 font-bold hover:underline"
          >
            {mode === "login" ? "Criar conta" : "Entrar"}
          </button>
        </p>

        <Link href="/" className="block mt-4 text-sm text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300 transition-colors">
          ← Voltar ao mapa
        </Link>
      </div>
    </div>
  );
}
