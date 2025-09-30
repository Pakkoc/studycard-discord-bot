import { getPool } from "@/lib/db";

export type GuildUserRow = {
  user_id: string; // serialized for JSON safety
  nickname: string | null;
  student_no: string | null;
  xp: number;
  total_seconds: number;
  today_seconds: number;
  week_seconds: number;
  month_seconds: number;
  last_seen_at: string | null;
};

export type SortKey =
  | "user_id"
  | "nickname"
  | "student_no"
  | "xp"
  | "total_seconds"
  | "today_seconds"
  | "week_seconds"
  | "month_seconds"
  | "last_seen_at";

export type SortOrder = "asc" | "desc";

export type FetchPagedOptions = {
  page?: number; // 1-based
  limit?: number; // page size
  sort?: SortKey;
  order?: SortOrder;
  query?: string;
};

export async function fetchGuildUserStats(
  guildId: bigint,
  limit = 100,
  query?: string
): Promise<GuildUserRow[]> {
  const pool = getPool();
  const client = await pool.connect();
  try {
    const params: unknown[] = [guildId.toString(), limit];
    let filterSql = "";
    if (query && query.trim().length > 0) {
      filterSql = " AND (u.nickname ILIKE $3 OR u.student_no ILIKE $3 OR CAST(u.user_id AS TEXT) ILIKE $3) ";
      params.push(`%${query.trim()}%`);
    }

    const sql = `
      SELECT
        u.user_id,
        u.nickname,
        u.student_no,
        COALESCE(u.xp, 0) AS xp,
        COALESCE(u.total_seconds, 0) AS total_seconds,
        COALESCE(SUM(CASE WHEN vs.ended_at >= date_trunc('day',   now()) THEN vs.duration_seconds END), 0) AS today_seconds,
        COALESCE(SUM(CASE WHEN vs.ended_at >= date_trunc('week',  now()) THEN vs.duration_seconds END), 0) AS week_seconds,
        COALESCE(SUM(CASE WHEN vs.ended_at >= date_trunc('month', now()) THEN vs.duration_seconds END), 0) AS month_seconds,
        to_char(u.last_seen_at, 'YYYY-MM-DD HH24:MI') AS last_seen_at
      FROM users u
      LEFT JOIN voice_sessions vs
        ON vs.user_id = u.user_id
       AND vs.guild_id = u.guild_id
       AND vs.ended_at IS NOT NULL
      WHERE u.guild_id = $1
      ${filterSql}
      GROUP BY u.user_id, u.nickname, u.student_no, u.xp, u.total_seconds, u.last_seen_at
      ORDER BY xp DESC, total_seconds DESC
      LIMIT $2
    `;

    const { rows } = await client.query(sql, params);

    return rows.map((r) => ({
      user_id: String(r.user_id),
      nickname: r.nickname ?? null,
      student_no: r.student_no ?? null,
      xp: Number(r.xp ?? 0),
      total_seconds: Number(r.total_seconds ?? 0),
      today_seconds: Number(r.today_seconds ?? 0),
      week_seconds: Number(r.week_seconds ?? 0),
      month_seconds: Number(r.month_seconds ?? 0),
      last_seen_at: (r.last_seen_at as string | null) ?? null,
    }));
  } finally {
    client.release();
  }
}

export async function fetchGuildUserStatsPaged(
  guildId: bigint,
  opts: FetchPagedOptions = {}
): Promise<{ rows: GuildUserRow[]; total: number }> {
  const pool = getPool();
  const client = await pool.connect();
  try {
    const limit = Math.min(Math.max(Number(opts.limit ?? 20), 1), 500);
    const page = Math.max(Number(opts.page ?? 1), 1);
    const offset = (page - 1) * limit;
    const sort: SortKey = (opts.sort as SortKey) ?? "xp";
    const order: SortOrder = (opts.order as SortOrder) ?? "desc";
    const query = (opts.query ?? "").trim();

    // Whitelist sort keys to avoid SQL injection
    const allowedSort: Record<SortKey, true> = {
      user_id: true,
      nickname: true,
      student_no: true,
      xp: true,
      total_seconds: true,
      today_seconds: true,
      week_seconds: true,
      month_seconds: true,
      last_seen_at: true,
    };
    const sortKey: SortKey = allowedSort[sort] ? sort : "xp";
    const sortOrder: SortOrder = order === "asc" ? "asc" : "desc";

    const params: unknown[] = [guildId.toString()];
    let filterSql = "";
    if (query.length > 0) {
      filterSql =
        " AND (u.nickname ILIKE $2 OR u.student_no ILIKE $2 OR CAST(u.user_id AS TEXT) ILIKE $2) ";
      params.push(`%${query}%`);
    }

    // Total count (from users table for pagination)
    const countSql = `
      SELECT COUNT(*)::int AS cnt
      FROM users u
      WHERE u.guild_id = $1
      ${filterSql}
    `;
    const { rows: countRows } = await client.query(countSql, params);
    const total = Number(countRows?.[0]?.cnt ?? 0);

    // Build main query with dynamic ORDER BY using a safe whitelist
    // Note: we can reference aliases (today_seconds etc.) in ORDER BY
    const baseParams = [...params];
    baseParams.push(limit);
    baseParams.push(offset);

    const limitIdx = baseParams.length - 1; // offset is last, limit is previous
    const offsetIdx = baseParams.length; // not used in query string directly below; indices are illustrative

    const sql = `
      SELECT
        u.user_id,
        u.nickname,
        u.student_no,
        COALESCE(u.xp, 0) AS xp,
        COALESCE(u.total_seconds, 0) AS total_seconds,
        COALESCE(SUM(CASE WHEN vs.ended_at >= date_trunc('day',   now()) THEN vs.duration_seconds END), 0) AS today_seconds,
        COALESCE(SUM(CASE WHEN vs.ended_at >= date_trunc('week',  now()) THEN vs.duration_seconds END), 0) AS week_seconds,
        COALESCE(SUM(CASE WHEN vs.ended_at >= date_trunc('month', now()) THEN vs.duration_seconds END), 0) AS month_seconds,
        to_char(u.last_seen_at, 'YYYY-MM-DD HH24:MI') AS last_seen_at
      FROM users u
      LEFT JOIN voice_sessions vs
        ON vs.user_id = u.user_id
       AND vs.guild_id = u.guild_id
       AND vs.ended_at IS NOT NULL
      WHERE u.guild_id = $1
      ${query.length > 0 ? " AND (u.nickname ILIKE $2 OR u.student_no ILIKE $2 OR CAST(u.user_id AS TEXT) ILIKE $2) " : ""}
      GROUP BY u.user_id, u.nickname, u.student_no, u.xp, u.total_seconds, u.last_seen_at
      ORDER BY ${sortKey} ${sortOrder} NULLS LAST
      LIMIT ${query.length > 0 ? "$3" : "$2"}
      OFFSET ${query.length > 0 ? "$4" : "$3"}
    `;

    const { rows } = await client.query(sql, baseParams);

    return {
      rows: rows.map((r) => ({
        user_id: String(r.user_id),
        nickname: r.nickname ?? null,
        student_no: r.student_no ?? null,
        xp: Number(r.xp ?? 0),
        total_seconds: Number(r.total_seconds ?? 0),
        today_seconds: Number(r.today_seconds ?? 0),
        week_seconds: Number(r.week_seconds ?? 0),
        month_seconds: Number(r.month_seconds ?? 0),
        last_seen_at: (r.last_seen_at as string | null) ?? null,
      })),
      total,
    };
  } finally {
    client.release();
  }
}


