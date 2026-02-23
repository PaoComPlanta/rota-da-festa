import { NextRequest, NextResponse } from "next/server";
import { createClient } from "@supabase/supabase-js";

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_KEY || process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
);

// GET /api/vou?event_id=xxx — get count for event
export async function GET(req: NextRequest) {
  const eventId = req.nextUrl.searchParams.get("event_id");
  if (!eventId) return NextResponse.json({ count: 0 });

  const { count } = await supabase
    .from("vou_eventos")
    .select("*", { count: "exact", head: true })
    .eq("evento_id", eventId);

  return NextResponse.json({ count: count || 0 });
}

// POST /api/vou — toggle vou for user
export async function POST(req: NextRequest) {
  try {
    const { event_id, user_id, action } = await req.json();
    if (!event_id || !user_id) {
      return NextResponse.json({ error: "Missing fields" }, { status: 400 });
    }

    if (action === "remove") {
      await supabase
        .from("vou_eventos")
        .delete()
        .match({ evento_id: event_id, user_id });
    } else {
      await supabase
        .from("vou_eventos")
        .upsert({ evento_id: event_id, user_id }, { onConflict: "evento_id,user_id" });
    }

    // Return updated count
    const { count } = await supabase
      .from("vou_eventos")
      .select("*", { count: "exact", head: true })
      .eq("evento_id", event_id);

    return NextResponse.json({ count: count || 0 });
  } catch (error) {
    return NextResponse.json({ error: "Server error" }, { status: 500 });
  }
}
