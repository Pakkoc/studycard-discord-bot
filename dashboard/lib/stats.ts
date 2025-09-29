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


