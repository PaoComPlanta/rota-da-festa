import { NextRequest, NextResponse } from "next/server";
import { createClient } from "@supabase/supabase-js";

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_KEY || process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
);

// GET /api/reviews?event_id=xxx
export async function GET(req: NextRequest) {
  const eventId = req.nextUrl.searchParams.get("event_id");
  if (!eventId) return NextResponse.json({ reviews: [] });

  const { data, error } = await supabase
    .from("reviews")
    .select("*")
    .eq("evento_id", eventId)
    .order("created_at", { ascending: false })
    .limit(20);

  if (error) return NextResponse.json({ reviews: [] });
  return NextResponse.json({ reviews: data || [] });
}

// POST /api/reviews — create review
export async function POST(req: NextRequest) {
  try {
    const formData = await req.formData();
    const evento_id = formData.get("evento_id") as string;
    const user_id = formData.get("user_id") as string;
    const user_name = formData.get("user_name") as string;
    const texto = formData.get("texto") as string;
    const rating = parseInt(formData.get("rating") as string) || 5;
    const foto = formData.get("foto") as File | null;

    if (!evento_id || !user_id || !texto) {
      return NextResponse.json({ error: "Missing fields" }, { status: 400 });
    }

    if (texto.length > 500) {
      return NextResponse.json({ error: "Review too long" }, { status: 400 });
    }

    let foto_url: string | null = null;

    // Upload photo if provided
    if (foto && foto.size > 0) {
      if (foto.size > 5 * 1024 * 1024) {
        return NextResponse.json({ error: "Foto demasiado grande (máx 5MB)" }, { status: 400 });
      }

      const ext = foto.name.split(".").pop() || "jpg";
      const path = `reviews/${evento_id}/${Date.now()}.${ext}`;

      const buffer = Buffer.from(await foto.arrayBuffer());
      const { error: uploadError } = await supabase.storage
        .from("fotos")
        .upload(path, buffer, { contentType: foto.type, upsert: false });

      if (!uploadError) {
        const { data: urlData } = supabase.storage.from("fotos").getPublicUrl(path);
        foto_url = urlData.publicUrl;
      }
    }

    const { data, error } = await supabase
      .from("reviews")
      .insert({
        evento_id,
        user_id,
        user_name: user_name || "Anónimo",
        texto,
        rating: Math.min(5, Math.max(1, rating)),
        foto_url,
      })
      .select()
      .single();

    if (error) {
      console.error("Review insert error:", error);
      return NextResponse.json({ error: "Erro ao guardar review" }, { status: 500 });
    }

    return NextResponse.json({ review: data });
  } catch (error) {
    console.error("Reviews API error:", error);
    return NextResponse.json({ error: "Server error" }, { status: 500 });
  }
}
