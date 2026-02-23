"use client";

import { useState } from "react";
import Link from "next/link";

const PLANS = [
  {
    id: "basico",
    name: "Básico",
    price: "10",
    features: ["📍 Pin no mapa", "📞 Nome + telefone", "📊 Estatísticas básicas"],
    color: "border-gray-300 dark:border-gray-600",
    popular: false,
  },
  {
    id: "destaque",
    name: "Destaque",
    price: "20",
    features: ["📍 Pin dourado no mapa", "🏷️ Banner nos eventos", "🎁 Cupão de desconto", "📊 Estatísticas avançadas"],
    color: "border-green-500 dark:border-green-400",
    popular: true,
  },
  {
    id: "premium",
    name: "Premium",
    price: "35",
    features: ["📍 Pin dourado + destaque", "🏷️ Banner nos eventos", "🎁 Cupão de desconto", "🔔 Notificação push", "📊 Dashboard completo"],
    color: "border-yellow-500 dark:border-yellow-400",
    popular: false,
  },
];

export default function NegociosPage() {
  const [loading, setLoading] = useState<string | null>(null);
  const [businessName, setBusinessName] = useState("");
  const [email, setEmail] = useState("");
  const [selectedPlan, setSelectedPlan] = useState<string | null>(null);
  const [message, setMessage] = useState<{ text: string; type: "success" | "error" } | null>(null);

  const params = typeof window !== "undefined" ? new URLSearchParams(window.location.search) : null;
  const isSuccess = params?.get("success") === "true";

  const handleCheckout = async (planId: string) => {
    if (!businessName.trim() || !email.trim()) {
      setMessage({ text: "Preenche o nome do negócio e o email.", type: "error" });
      setSelectedPlan(planId);
      return;
    }

    setLoading(planId);
    setMessage(null);

    try {
      const res = await fetch("/api/stripe/checkout", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ plan: planId, businessName: businessName.trim(), email: email.trim() }),
      });
      const data = await res.json();

      if (data.url) {
        window.location.href = data.url;
      } else {
        setMessage({ text: data.error || "Erro ao criar sessão de pagamento.", type: "error" });
      }
    } catch {
      setMessage({ text: "Erro de ligação. Tenta novamente.", type: "error" });
    } finally {
      setLoading(null);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950 text-gray-900 dark:text-gray-100 transition-colors">
      {/* Hero */}
      <div className="bg-gradient-to-br from-green-600 via-emerald-600 to-blue-600 text-white">
        <div className="max-w-5xl mx-auto px-4 py-16 text-center">
          <Link href="/" className="inline-flex items-center gap-2 text-green-100 hover:text-white mb-6 transition-colors text-sm font-medium">
            ← Voltar ao mapa
          </Link>
          <h1 className="text-4xl md:text-5xl font-extrabold mb-4">
            🏪 Ponha o seu negócio no mapa
          </h1>
          <p className="text-lg md:text-xl text-green-100 max-w-2xl mx-auto mb-8">
            Milhares de pessoas usam a Rota da Festa para encontrar eventos perto de si.
            O seu restaurante, café ou loja pode aparecer no mapa, junto aos eventos.
          </p>
          <div className="flex flex-wrap justify-center gap-6 text-sm font-bold">
            <div className="flex items-center gap-2"><span className="text-2xl">📍</span> Pin no mapa interativo</div>
            <div className="flex items-center gap-2"><span className="text-2xl">🎁</span> Cupões de desconto</div>
            <div className="flex items-center gap-2"><span className="text-2xl">📊</span> Estatísticas de visualizações</div>
          </div>
        </div>
      </div>

      {/* Success banner */}
      {isSuccess && (
        <div className="bg-green-100 dark:bg-green-900/50 border-b border-green-200 dark:border-green-800 p-4 text-center">
          <p className="text-green-800 dark:text-green-200 font-bold">🎉 Pagamento confirmado! Entraremos em contacto em breve para configurar o seu pin no mapa.</p>
        </div>
      )}

      {/* Business info form */}
      <div className="max-w-5xl mx-auto px-4 py-12">
        <div className="max-w-md mx-auto mb-12 space-y-4">
          <h2 className="text-xl font-bold text-center mb-2">Informações do Negócio</h2>
          <input
            type="text"
            placeholder="Nome do negócio"
            value={businessName}
            onChange={(e) => setBusinessName(e.target.value)}
            className="w-full bg-white dark:bg-gray-800 text-gray-900 dark:text-white border border-gray-300 dark:border-gray-600 rounded-xl px-4 py-3 focus:ring-2 focus:ring-green-500 outline-none transition-colors"
          />
          <input
            type="email"
            placeholder="Email de contacto"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="w-full bg-white dark:bg-gray-800 text-gray-900 dark:text-white border border-gray-300 dark:border-gray-600 rounded-xl px-4 py-3 focus:ring-2 focus:ring-green-500 outline-none transition-colors"
          />
          {message && (
            <p className={`text-sm font-medium text-center ${message.type === "error" ? "text-red-500" : "text-green-600"}`}>
              {message.text}
            </p>
          )}
        </div>

        {/* Pricing cards */}
        <div className="grid md:grid-cols-3 gap-6 max-w-4xl mx-auto">
          {PLANS.map((plan) => (
            <div
              key={plan.id}
              className={`relative bg-white dark:bg-gray-900 rounded-2xl shadow-lg border-2 ${plan.color} p-6 flex flex-col transition-transform hover:scale-[1.02] ${selectedPlan === plan.id ? "ring-2 ring-green-500" : ""}`}
            >
              {plan.popular && (
                <span className="absolute -top-3 left-1/2 -translate-x-1/2 bg-green-600 text-white text-xs font-bold px-4 py-1 rounded-full">
                  ⭐ Mais popular
                </span>
              )}
              <h3 className="text-xl font-bold mb-1">{plan.name}</h3>
              <div className="flex items-baseline gap-1 mb-4">
                <span className="text-4xl font-extrabold">{plan.price}€</span>
                <span className="text-gray-500 dark:text-gray-400 text-sm">/mês</span>
              </div>
              <ul className="space-y-2 mb-6 flex-1">
                {plan.features.map((f) => (
                  <li key={f} className="text-sm text-gray-700 dark:text-gray-300 flex items-center gap-2">
                    <span className="text-green-500">✓</span> {f}
                  </li>
                ))}
              </ul>
              <button
                onClick={() => handleCheckout(plan.id)}
                disabled={loading === plan.id}
                className={`w-full py-3 rounded-xl font-bold text-sm transition-colors active:scale-[0.98] ${
                  plan.popular
                    ? "bg-green-600 text-white hover:bg-green-700"
                    : "bg-gray-100 dark:bg-gray-800 text-gray-900 dark:text-white hover:bg-gray-200 dark:hover:bg-gray-700 border border-gray-200 dark:border-gray-700"
                } disabled:opacity-50`}
              >
                {loading === plan.id ? "A processar..." : "Escolher Plano"}
              </button>
            </div>
          ))}
        </div>

        {/* FAQ */}
        <div className="max-w-2xl mx-auto mt-16 space-y-6">
          <h2 className="text-2xl font-bold text-center mb-8">Perguntas Frequentes</h2>
          {[
            { q: "Como funciona?", a: "Depois do pagamento, entramos em contacto para configurar o seu pin no mapa com a localização, nome, telefone e cupão de desconto." },
            { q: "Posso cancelar?", a: "Sim, pode cancelar a qualquer momento. A subscrição é mensal sem compromisso." },
            { q: "Quando aparece no mapa?", a: "Em menos de 24 horas após o pagamento, o seu negócio estará visível para todos os utilizadores." },
            { q: "Que resultados posso esperar?", a: "Os utilizadores vêem o seu negócio quando estão a caminho de um evento. É publicidade hiperlocal com alta intenção de compra." },
          ].map(({ q, a }) => (
            <div key={q} className="bg-white dark:bg-gray-900 rounded-xl p-5 border border-gray-200 dark:border-gray-700">
              <h3 className="font-bold text-gray-900 dark:text-white mb-1">{q}</h3>
              <p className="text-sm text-gray-600 dark:text-gray-400">{a}</p>
            </div>
          ))}
        </div>

        {/* CTA */}
        <div className="text-center mt-16 pb-8">
          <p className="text-gray-500 dark:text-gray-400 text-sm mb-4">
            Dúvidas? Contacta-nos em <a href="mailto:rotadafesta@gmail.com" className="text-blue-600 dark:text-blue-400 hover:underline font-medium">rotadafesta@gmail.com</a>
          </p>
          <Link href="/" className="text-sm text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300">
            ← Voltar ao mapa
          </Link>
        </div>
      </div>
    </div>
  );
}
