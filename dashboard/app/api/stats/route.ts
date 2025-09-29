import { NextRequest } from "next/server";
import { fetchGuildUserStats } from "@/lib/stats";

export const dynamic = "force-dynamic";

export async function GET(req: NextRequest) {
  const { searchParams } = new URL(req.url);
  const guildId = process.env.DEFAULT_GUILD_ID || process.env.DEV_GUILD_ID || "";
  const limit = Number(searchParams.get("limit") || 500);
  const q = searchParams.get("q") || undefined;

  if (!guildId) {
    return new Response(JSON.stringify({ error: "guild_id is required" }), { status: 400 });
  }

  try {
    const data = await fetchGuildUserStats(BigInt(guildId), Math.min(Math.max(limit, 1), 500), q);
    return Response.json({ data });
  } catch (err: unknown) {
    console.error(err);
    return new Response(JSON.stringify({ error: "failed to load stats" }), { status: 500 });
  }
}


