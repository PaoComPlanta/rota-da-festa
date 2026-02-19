"use client";

import { useState } from "react";
import { supabase } from "@/utils/supabase/client";
import Link from "next/link";

export default function SubmitEvent() {
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [formData, setFormData] = useState({
    nome: "",
    tipo: "Futebol",
    data: "",
    hora: "",
    local: "",
    preco: "",
    descricao: "",
  });

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    // Preparar objeto para envio
    const eventoParaEnviar = {
      ...formData,
      status: "pendente", // FORÇADO: Utilizador não pode aprovar
      latitude: null,     // Admin terá de preencher depois
      longitude: null,
    };

    const { error } = await supabase.from("eventos").insert([eventoParaEnviar]);

    setLoading(false);

    if (error) {
      console.error("Erro ao submeter:", error);
      alert("Ocorreu um erro ao submeter o evento. Tenta novamente.");
    } else {
      setSuccess(true);
      setFormData({
        nome: "",
        tipo: "Futebol",
        data: "",
        hora: "",
        local: "",
        preco: "",
        descricao: "",
      });
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950 py-12 px-4 sm:px-6 lg:px-8 transition-colors">
      <div className="max-w-md mx-auto bg-white dark:bg-gray-900 rounded-xl shadow-lg overflow-hidden border border-gray-100 dark:border-gray-800">
        
        {/* Header */}
        <div className="bg-gradient-to-r from-green-600 to-blue-600 px-6 py-4">
          <h2 className="text-2xl font-bold text-white text-center">
            Submeter Evento
          </h2>
          <p className="text-green-100 text-center text-sm mt-1">
            Ajuda a comunidade a crescer!
          </p>
        </div>

        {/* Success Message */}
        {success ? (
          <div className="p-8 text-center animate-fade-in">
            <div className="mx-auto flex items-center justify-center h-16 w-16 rounded-full bg-green-100 dark:bg-green-900/30 mb-4">
              <span className="text-3xl">🎉</span>
            </div>
            <h3 className="text-xl font-bold text-gray-900 dark:text-white mb-2">
              Evento Recebido!
            </h3>
            <p className="text-gray-600 dark:text-gray-300 mb-6">
              O teu evento foi submetido com sucesso e ficará visível após aprovação da nossa equipa.
            </p>
            <button
              onClick={() => setSuccess(false)}
              className="w-full bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-200 font-bold py-2 px-4 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors"
            >
              Submeter outro
            </button>
            <Link href="/" className="block mt-4 text-blue-600 dark:text-blue-400 hover:underline text-sm">
              Voltar ao Mapa
            </Link>
          </div>
        ) : (
          /* Form */
          <form onSubmit={handleSubmit} className="p-6 space-y-4">
            
            {/* Nome */}
            <div>
              <label htmlFor="nome" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                Nome do Evento *
              </label>
              <input
                type="text"
                name="nome"
                id="nome"
                required
                value={formData.nome}
                onChange={handleChange}
                placeholder="Ex: Feirense vs Oliveirense"
                className="mt-1 block w-full rounded-lg border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-white shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm p-2.5 transition-colors"
              />
            </div>

            {/* Tipo e Data (Grid) */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label htmlFor="tipo" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                  Tipo *
                </label>
                <select
                  name="tipo"
                  id="tipo"
                  value={formData.tipo}
                  onChange={handleChange}
                  className="mt-1 block w-full rounded-lg border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-white shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm p-2.5 transition-colors"
                >
                  <option value="Futebol">⚽ Futebol</option>
                  <option value="Festa/Romaria">🎉 Festa/Romaria</option>
                  <option value="Cultura/Lazer">🎭 Cultura/Lazer</option>
                </select>
              </div>

              <div>
                <label htmlFor="data" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                  Data *
                </label>
                <input
                  type="date"
                  name="data"
                  id="data"
                  required
                  value={formData.data}
                  onChange={handleChange}
                  className="mt-1 block w-full rounded-lg border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-white shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm p-2.5 transition-colors"
                />
              </div>
            </div>

            {/* Hora e Preço (Grid) */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label htmlFor="hora" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                  Hora *
                </label>
                <input
                  type="time"
                  name="hora"
                  id="hora"
                  required
                  value={formData.hora}
                  onChange={handleChange}
                  className="mt-1 block w-full rounded-lg border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-white shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm p-2.5 transition-colors"
                />
              </div>

              <div>
                <label htmlFor="preco" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                  Preço
                </label>
                <input
                  type="text"
                  name="preco"
                  id="preco"
                  value={formData.preco}
                  onChange={handleChange}
                  placeholder="Ex: Grátis ou 5€"
                  className="mt-1 block w-full rounded-lg border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-white shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm p-2.5 transition-colors"
                />
              </div>
            </div>

            {/* Local */}
            <div>
              <label htmlFor="local" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                Local (Nome/Morada) *
              </label>
              <input
                type="text"
                name="local"
                id="local"
                required
                value={formData.local}
                onChange={handleChange}
                placeholder="Ex: Estádio do Bessa, Porto"
                className="mt-1 block w-full rounded-lg border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-white shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm p-2.5 transition-colors"
              />
            </div>

            {/* Submit Button */}
            <div className="pt-4">
              <button
                type="submit"
                disabled={loading}
                className={`w-full flex justify-center py-3 px-4 border border-transparent rounded-lg shadow-sm text-sm font-bold text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors ${
                  loading ? "opacity-75 cursor-not-allowed" : ""
                }`}
              >
                {loading ? "A enviar..." : "Enviar Evento 🚀"}
              </button>
            </div>
            
            <div className="text-center mt-2">
                 <Link href="/" className="text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 text-sm">
                    Cancelar
                 </Link>
            </div>

          </form>
        )}
      </div>
    </div>
  );
}
