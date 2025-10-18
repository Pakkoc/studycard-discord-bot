import { NextRequest } from "next/server";
import {
  fetchGuildUserStats,
  fetchGuildUserStatsPaged,
  fetchUserDetail,
  fetchUserEntryLogs,
  fetchUserDailyTrend,
  fetchUserWeekdayHourHeatmap,
} from "@/lib/stats";

export const dynamic = "force-dynamic";

export async function GET(req: NextRequest) {
  const { searchParams } = new URL(req.url);
  const guildId = process.env.DEFAULT_GUILD_ID || process.env.DEV_GUILD_ID || "";
  const userIdParam = searchParams.get("user_id");
  const limit = Number(searchParams.get("limit") || 20);
  const q = searchParams.get("q") || undefined;
  const page = Number(searchParams.get("page") || 1);
  const sort = (searchParams.get("sort") || undefined) as any;
  const order = (searchParams.get("order") || undefined) as any;
  const scope = searchParams.get("scope") || undefined; // detail | logs | trend | heatmap
  const days = Number(searchParams.get("days") || 30);

  if (!guildId) {
    return new Response(JSON.stringify({ error: "guild_id is required" }), { status: 400 });
  }

  try {
    // User scoped endpoints
    if (userIdParam && scope) {
      const userId = BigInt(userIdParam);
      if (scope === "detail") {
        const data = await fetchUserDetail(BigInt(guildId), userId);
        return Response.json({ data });
      }
      if (scope === "logs") {
        const data = await fetchUserEntryLogs(BigInt(guildId), userId, Math.min(Math.max(limit, 1), 500));
        return Response.json({ data });
      }
      if (scope === "trend") {
        const data = await fetchUserDailyTrend(BigInt(guildId), userId, Math.min(Math.max(days, 1), 180));
        return Response.json({ data });
      }
      if (scope === "heatmap") {
        const data = await fetchUserWeekdayHourHeatmap(BigInt(guildId), userId, Math.min(Math.max(days, 1), 365));
        return Response.json({ data });
      }
      return new Response(JSON.stringify({ error: "invalid scope" }), { status: 400 });
    }

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


