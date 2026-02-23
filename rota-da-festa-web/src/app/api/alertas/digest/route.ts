import { NextRequest, NextResponse } from "next/server";
import { createClient } from "@supabase/supabase-js";
import { Resend } from "resend";

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_KEY || process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
);

const DISTRICT_CENTROIDS: Record<string, { lat: number; lon: number }> = {
  "Braga": { lat: 41.5503, lon: -8.4270 },
  "Porto": { lat: 41.1496, lon: -8.6109 },
  "Aveiro": { lat: 40.6405, lon: -8.6538 },
  "Lisboa": { lat: 38.7223, lon: -9.1393 },
  "Leiria": { lat: 39.7437, lon: -8.8070 },
  "Coimbra": { lat: 40.2109, lon: -8.4377 },
  "Viseu": { lat: 40.6610, lon: -7.9097 },
  "Setúbal": { lat: 38.5244, lon: -8.8882 },
  "Santarém": { lat: 39.2369, lon: -8.6850 },
  "Beja": { lat: 38.0150, lon: -7.8653 },
  "Faro": { lat: 37.0194, lon: -7.9304 },
  "Évora": { lat: 38.5667, lon: -7.9000 },
  "Bragança": { lat: 41.8063, lon: -6.7572 },
  "Castelo Branco": { lat: 39.8228, lon: -7.4906 },
  "Guarda": { lat: 40.5373, lon: -7.2676 },
  "Viana do Castelo": { lat: 41.6936, lon: -8.8319 },
  "Vila Real": { lat: 41.2959, lon: -7.7464 },
  "Portalegre": { lat: 39.2967, lon: -7.4317 },
  "Madeira": { lat: 32.6669, lon: -16.9241 },
  "Açores": { lat: 37.7483, lon: -25.6666 },
};

function haversine(lat1: number, lon1: number, lat2: number, lon2: number) {
  const R = 6371;
  const dLat = ((lat2 - lat1) * Math.PI) / 180;
  const dLon = ((lon2 - lon1) * Math.PI) / 180;
  const a = Math.sin(dLat / 2) ** 2 + Math.cos((lat1 * Math.PI) / 180) * Math.cos((lat2 * Math.PI) / 180) * Math.sin(dLon / 2) ** 2;
  return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

// POST /api/alertas/digest — send weekly email digests (called by cron)
export async function POST(req: NextRequest) {
  const authHeader = req.headers.get("authorization");
  const cronSecret = process.env.CRON_SECRET;
  if (cronSecret && authHeader !== `Bearer ${cronSecret}`) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const resendKey = process.env.RESEND_API_KEY;
  if (!resendKey) {
    return NextResponse.json({ error: "RESEND_API_KEY not configured" }, { status: 500 });
  }

  const resend = new Resend(resendKey);

  try {
    const { data: subs } = await supabase.from("alertas").select("*").eq("ativo", true);
    if (!subs || subs.length === 0) {
      return NextResponse.json({ sent: 0, message: "No active subscribers" });
    }

    const today = new Date().toISOString().split("T")[0];
    const nextWeek = new Date(Date.now() + 7 * 86400000).toISOString().split("T")[0];
    const { data: events } = await supabase
      .from("eventos")
      .select("*")
      .gte("data", today)
      .lte("data", nextWeek)
      .in("status", ["aprovado", "adiado"])
      .order("data", { ascending: true });

    if (!events || events.length === 0) {
      return NextResponse.json({ sent: 0, message: "No events this week" });
    }

    const subsByDistrito: Record<string, string[]> = {};
    for (const sub of subs) {
      if (!subsByDistrito[sub.distrito]) subsByDistrito[sub.distrito] = [];
      subsByDistrito[sub.distrito].push(sub.email);
    }

    let sent = 0;
    const baseUrl = "https://rotadafesta.vercel.app";

    for (const [distrito, emails] of Object.entries(subsByDistrito)) {
      const center = DISTRICT_CENTROIDS[distrito];
      if (!center) continue;

      const districtEvents = events.filter(
        (ev: any) => ev.latitude && ev.longitude && haversine(center.lat, center.lon, ev.latitude, ev.longitude) <= 60
      );

      if (districtEvents.length === 0) continue;

      const eventRows = districtEvents.slice(0, 15).map((ev: any) => `
        <tr>
          <td style="padding:10px 16px;border-bottom:1px solid #e5e7eb;">
            <strong style="color:#111827;">${ev.nome}</strong><br>
            <span style="color:#6b7280;font-size:13px;">📅 ${ev.data} · 🕒 ${ev.hora} · 📍 ${ev.local}</span>
            ${ev.status === "adiado" ? '<br><span style="color:#f59e0b;font-size:12px;font-weight:bold;">⚠️ ADIADO</span>' : ""}
          </td>
        </tr>
      `).join("");

      const html = `
        <div style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;max-width:600px;margin:0 auto;">
          <div style="background:linear-gradient(135deg,#16a34a,#2563eb);padding:24px;border-radius:12px 12px 0 0;">
            <h1 style="color:white;margin:0;font-size:22px;">🎉 Rota da Festa</h1>
            <p style="color:#bbf7d0;margin:4px 0 0;font-size:14px;">Eventos esta semana em ${distrito}</p>
          </div>
          <div style="background:white;padding:20px;border:1px solid #e5e7eb;border-top:none;border-radius:0 0 12px 12px;">
            <p style="color:#374151;margin:0 0 16px;">Olá! 👋 Encontrámos <strong>${districtEvents.length} eventos</strong> perto de ${distrito} esta semana:</p>
            <table style="width:100%;border-collapse:collapse;font-size:14px;">${eventRows}</table>
            ${districtEvents.length > 15 ? `<p style="color:#6b7280;font-size:13px;margin-top:12px;">...e mais ${districtEvents.length - 15} eventos.</p>` : ""}
            <div style="text-align:center;margin-top:24px;">
              <a href="${baseUrl}" style="display:inline-block;background:#16a34a;color:white;font-weight:bold;padding:12px 24px;border-radius:8px;text-decoration:none;font-size:14px;">Ver no Mapa 🗺️</a>
            </div>
            <p style="color:#9ca3af;font-size:11px;margin-top:24px;text-align:center;">
              Recebeste este email porque subscreveste alertas para ${distrito}.<br>
              <a href="${baseUrl}" style="color:#3b82f6;">Cancelar subscrição</a>
            </p>
          </div>
        </div>
      `;

      for (const email of emails) {
        try {
          await resend.emails.send({
            from: "Rota da Festa <noreply@rotadafesta.pt>",
            to: email,
            subject: `🎉 ${districtEvents.length} eventos em ${distrito} esta semana`,
            html,
          });
          sent++;
        } catch (e) {
          console.error(`Erro email ${email}:`, e);
        }
      }
    }

    return NextResponse.json({ sent, subscribers: subs.length });
  } catch (e) {
    console.error("Erro digest:", e);
    return NextResponse.json({ error: "Erro interno" }, { status: 500 });
  }
}
