import { NextRequest } from "next/server";
import { fetchGuildUserStats, fetchGuildUserStatsPaged } from "@/lib/stats";

export const dynamic = "force-dynamic";

export async function GET(req: NextRequest) {
  const { searchParams } = new URL(req.url);
  const guildId = process.env.DEFAULT_GUILD_ID || process.env.DEV_GUILD_ID || "";
  const limit = Number(searchParams.get("limit") || 20);
  const q = searchParams.get("q") || undefined;
  const page = Number(searchParams.get("page") || 1);
  const sort = (searchParams.get("sort") || undefined) as any;
  const order = (searchParams.get("order") || undefined) as any;

  if (!guildId) {
    return new Response(JSON.stringify({ error: "guild_id is required" }), { status: 400 });
  }

  try {
    // Backward compatible: if page param is absent and limit>20, keep legacy path
    if (!searchParams.has("page") && limit > 20 && !sort && !order) {
      const data = await fetchGuildUserStats(BigInt(guildId), Math.min(Math.max(limit, 1), 500), q);
      return Response.json({ data, total: data.length });
    }
    const { rows, total } = await fetchGuildUserStatsPaged(BigInt(guildId), {
      page,
      limit: Math.min(Math.max(limit, 1), 500),
      sort,
      order,
      query: q,
    });
    return Response.json({ data: rows, total, page, limit });
  } catch (err: unknown) {
    console.error(err);
    return new Response(JSON.stringify({ error: "failed to load stats" }), { status: 500 });
  }
}


