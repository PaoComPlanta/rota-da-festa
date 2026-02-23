import { NextRequest, NextResponse } from "next/server";
import { createClient } from "@supabase/supabase-js";

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_KEY || process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
);

// GET /api/negocios?lat=41.55&lon=-8.42&radius=3
export async function GET(req: NextRequest) {
  const lat = parseFloat(req.nextUrl.searchParams.get("lat") || "0");
  const lon = parseFloat(req.nextUrl.searchParams.get("lon") || "0");
  const radius = parseFloat(req.nextUrl.searchParams.get("radius") || "3"); // km

  if (!lat || !lon) return NextResponse.json({ negocios: [] });

  // Fetch all active businesses and filter by distance
  const { data, error } = await supabase
    .from("negocios")
    .select("*")
    .eq("ativo", true);

  if (error || !data) return NextResponse.json({ negocios: [] });

  // Filter by radius (Haversine)
  const nearby = data.filter((n) => {
    const R = 6371;
    const dLat = ((n.latitude - lat) * Math.PI) / 180;
    const dLon = ((n.longitude - lon) * Math.PI) / 180;
    const a =
      Math.sin(dLat / 2) ** 2 +
      Math.cos((lat * Math.PI) / 180) * Math.cos((n.latitude * Math.PI) / 180) * Math.sin(dLon / 2) ** 2;
    const d = R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    return d <= radius;
  }).slice(0, 5);

  return NextResponse.json({ negocios: nearby });
}
