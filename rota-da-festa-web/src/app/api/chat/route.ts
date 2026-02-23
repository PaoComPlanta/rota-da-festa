import { NextRequest, NextResponse } from "next/server";
import { createClient } from "@supabase/supabase-js";

const GROQ_API_KEY = process.env.GROQ_API_KEY;
const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL!;
const SUPABASE_KEY = process.env.SUPABASE_SERVICE_KEY || process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!;

const supabase = createClient(SUPABASE_URL, SUPABASE_KEY);

async function getEventContext(): Promise<string> {
  const today = new Date().toISOString().split("T")[0];
  const nextWeek = new Date(Date.now() + 7 * 86400000).toISOString().split("T")[0];

  const { data } = await supabase
    .from("eventos")
    .select("nome, data, hora, local, categoria, escalao, tipo, status")
    .gte("data", today)
    .lte("data", nextWeek)
    .in("status", ["aprovado", "adiado"])
    .order("data")
    .limit(50);

  if (!data || data.length === 0) return "Não há eventos registados para esta semana.";

  return data
    .map((e) => `- ${e.nome} | ${e.data} ${e.hora || ""} | ${e.local || "Local TBD"} | ${e.categoria || e.tipo} ${e.escalao ? `(${e.escalao})` : ""} ${e.status === "adiado" ? "[ADIADO]" : ""}`)
    .join("\n");
}

export async function POST(req: NextRequest) {
  if (!GROQ_API_KEY) {
    return NextResponse.json({ reply: "Chatbot indisponível — GROQ_API_KEY não configurada." }, { status: 503 });
  }

  try {
    const { message } = await req.json();
    if (!message || typeof message !== "string" || message.length > 500) {
      return NextResponse.json({ reply: "Mensagem inválida." }, { status: 400 });
    }

    const eventContext = await getEventContext();

    const response = await fetch("https://api.groq.com/openai/v1/chat/completions", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${GROQ_API_KEY}`,
      },
      body: JSON.stringify({
        model: "llama-3.3-70b-versatile",
        messages: [
          {
            role: "system",
            content: `És o assistente da Rota da Festa, uma app portuguesa que mostra eventos de futebol e festas populares num mapa interativo.
Responde SEMPRE em português de Portugal, de forma simpática, curta e útil (máx 3 frases).
Usa emojis. Se te perguntarem sobre eventos, usa APENAS os dados abaixo. Não inventes eventos.
Se não souberes, diz "Não encontrei essa informação, mas podes explorar o mapa! 🗺️"

EVENTOS DESTA SEMANA:
${eventContext}`,
          },
          { role: "user", content: message },
        ],
        temperature: 0.7,
        max_tokens: 300,
      }),
    });

    if (!response.ok) {
      const err = await response.text();
      console.error("Groq API error:", err);
      return NextResponse.json({ reply: "Erro ao contactar o assistente. Tenta novamente! 🔄" }, { status: 502 });
    }

    const data = await response.json();
    const reply = data.choices?.[0]?.message?.content || "Desculpa, não consegui responder. 🤔";

    return NextResponse.json({ reply });
  } catch (error) {
    console.error("Chat API error:", error);
    return NextResponse.json({ reply: "Erro interno. Tenta novamente! 🔄" }, { status: 500 });
  }
}
