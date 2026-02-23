import { NextRequest, NextResponse } from "next/server";

const GROQ_API_KEY = process.env.GROQ_API_KEY;

interface ModerationResult {
  approved: boolean;
  category?: string;
  reason?: string;
}

export async function POST(req: NextRequest): Promise<NextResponse<ModerationResult>> {
  if (!GROQ_API_KEY) {
    // Without Groq, auto-approve (manual moderation via status='pendente')
    return NextResponse.json({ approved: true });
  }

  try {
    const { nome, tipo, data, hora, local, preco, descricao } = await req.json();

    const eventText = `Nome: ${nome}\nTipo: ${tipo}\nData: ${data}\nHora: ${hora}\nLocal: ${local}\nPreço: ${preco}\nDescrição: ${descricao || "N/A"}`;

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
            content: `És um moderador de eventos para a app Rota da Festa (Portugal).
Analisa o evento submetido e responde APENAS com JSON válido:
{"approved": true/false, "category": "sugerida", "reason": "motivo se rejeitado"}

Regras:
- APROVA eventos legítimos: jogos de futebol, festas populares, romarias, feiras, concertos, eventos culturais/desportivos em Portugal.
- REJEITA: spam, conteúdo ofensivo, publicidade disfarçada, eventos falsos/impossíveis, conteúdo sexual/violento.
- Para "category", sugere uma de: Futebol, Festa/Romaria, Concerto, Feira, Teatro, Cultura, Desporto, Tradição.
- Sê permissivo — em caso de dúvida, aprova.`,
          },
          { role: "user", content: eventText },
        ],
        temperature: 0.1,
        max_tokens: 150,
      }),
    });

    if (!response.ok) {
      console.error("Groq moderation error:", await response.text());
      return NextResponse.json({ approved: true }); // Fail-open
    }

    const data_resp = await response.json();
    const content = data_resp.choices?.[0]?.message?.content || "";

    // Parse JSON from response (may have markdown wrapping)
    const jsonMatch = content.match(/\{[\s\S]*\}/);
    if (jsonMatch) {
      const parsed = JSON.parse(jsonMatch[0]);
      return NextResponse.json({
        approved: parsed.approved !== false,
        category: parsed.category,
        reason: parsed.reason,
      });
    }

    return NextResponse.json({ approved: true }); // Can't parse → approve
  } catch (error) {
    console.error("Moderation error:", error);
    return NextResponse.json({ approved: true }); // Fail-open
  }
}
