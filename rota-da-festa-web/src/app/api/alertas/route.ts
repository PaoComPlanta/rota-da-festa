import { NextRequest, NextResponse } from "next/server";
import { createClient } from "@supabase/supabase-js";

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_KEY || process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
);

// POST /api/alertas — subscribe to district alerts
export async function POST(req: NextRequest) {
  try {
    const { email, distrito } = await req.json();
    if (!email || !distrito) {
      return NextResponse.json({ error: "Email e distrito são obrigatórios" }, { status: 400 });
    }

    const { error } = await supabase
      .from("alertas")
      .upsert({ email, distrito, ativo: true }, { onConflict: "email,distrito" });

    if (error) {
      console.error("Erro alertas:", error);
      return NextResponse.json({ error: "Erro ao guardar alerta" }, { status: 500 });
    }

    return NextResponse.json({ ok: true, message: "Alerta criado com sucesso!" });
  } catch {
    return NextResponse.json({ error: "Erro interno" }, { status: 500 });
  }
}

// DELETE /api/alertas — unsubscribe
export async function DELETE(req: NextRequest) {
  try {
    const { email, distrito } = await req.json();
    if (!email) {
      return NextResponse.json({ error: "Email obrigatório" }, { status: 400 });
    }

    const query = supabase.from("alertas").delete().eq("email", email);
    if (distrito) query.eq("distrito", distrito);
    await query;

    return NextResponse.json({ ok: true });
  } catch {
    return NextResponse.json({ error: "Erro interno" }, { status: 500 });
  }
}
