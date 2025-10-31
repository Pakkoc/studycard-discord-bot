import { getPool } from "@/lib/db";

export type SummaryToday = {
  todayHours: number;
  dau: number;
  avgHoursPerActive: number;
};

export async function fetchSummaryToday(guildId: bigint): Promise<SummaryToday> {
  const pool = getPool();
  const client = await pool.connect();
  try {
    const { rows } = await client.query(
      `
      WITH kstart AS (
        SELECT ((date_trunc('day', (now() AT TIME ZONE 'Asia/Seoul') - interval '6 hour') + interval '6 hour') AT TIME ZONE 'Asia/Seoul') AS s
      )
      SELECT
        COALESCE(SUM(CASE WHEN ended_at >= (SELECT s FROM kstart) THEN duration_seconds END), 0) AS today_seconds,
        COALESCE(COUNT(DISTINCT CASE WHEN ended_at >= (SELECT s FROM kstart) THEN user_id END), 0) AS dau
      FROM voice_sessions
      WHERE guild_id = $1 AND ended_at IS NOT NULL
      `,
      [guildId.toString()]
    );
    const todaySeconds = Number(rows?.[0]?.today_seconds ?? 0);
    const dau = Number(rows?.[0]?.dau ?? 0);
    const todayHours = Math.round((todaySeconds / 3600) * 100) / 100;
    const avg = dau > 0 ? Math.round((todayHours / dau) * 100) / 100 : 0;
    return { todayHours, dau, avgHoursPerActive: avg };
  } finally {
    client.release();
  }
}

export type DailyTrendPoint = { date: string; hours: number; dau: number };

export async function fetchDailyTrend(guildId: bigint, days = 30): Promise<DailyTrendPoint[]> {
  const pool = getPool();
  const client = await pool.connect();
  try {
    const start = new Date();
    start.setDate(start.getDate() - (days - 1));
    const { rows } = await client.query(
      `
      WITH start_bound AS (
        SELECT date_trunc('day', $2::timestamptz AT TIME ZONE 'Asia/Seoul') AS start_day
      )
      SELECT to_char(date_trunc('day', ended_at AT TIME ZONE 'Asia/Seoul'), 'YYYY-MM-DD') AS day_label,
             SUM(duration_seconds) AS seconds,
             COUNT(DISTINCT user_id) AS dau
      FROM voice_sessions
      WHERE guild_id=$1 AND ended_at IS NOT NULL
        AND (ended_at AT TIME ZONE 'Asia/Seoul') >= (SELECT start_day FROM start_bound)
      GROUP BY day_label
      ORDER BY day_label
      `,
      [guildId.toString(), start]
    );
    const map = new Map<string, { seconds: number; dau: number }>();
    for (const r of rows) {
      const day = String(r.day_label);
      map.set(day, { seconds: Number(r.seconds ?? 0), dau: Number(r.dau ?? 0) });
    }
    const out: DailyTrendPoint[] = [];
    for (let i = 0; i < days; i++) {
      const d = new Date(start);
      d.setDate(start.getDate() + i);
      const key = d.toISOString().slice(0, 10);
      const v = map.get(key) ?? { seconds: 0, dau: 0 };
      out.push({ date: key, hours: Math.round((v.seconds / 3600) * 100) / 100, dau: v.dau });
    }
    return out;
  } finally {
    client.release();
  }
}

export type LeaderRow = { user_id: string; nickname: string | null; value_seconds: number };

export async function fetchLeaderboard(
  guildId: bigint,
  period: "week" | "month"
): Promise<LeaderRow[]> {
  const pool = getPool();
  const client = await pool.connect();
  try {
    const boundColumn = period === "week" ? "week_start" : "month_start";
    const fieldExpr = `CASE WHEN vs.ended_at >= (SELECT ${boundColumn} FROM bounds) THEN vs.duration_seconds END`;
    const sql = `
      WITH bounds AS (
        SELECT
          ((date_trunc('week',  now() AT TIME ZONE 'Asia/Seoul')) AT TIME ZONE 'Asia/Seoul') AS week_start,
          ((date_trunc('month', now() AT TIME ZONE 'Asia/Seoul')) AT TIME ZONE 'Asia/Seoul') AS month_start
      )
      SELECT u.user_id::text AS user_id, u.nickname,
             COALESCE(SUM(${fieldExpr}), 0) AS value_seconds
      FROM users u
      LEFT JOIN voice_sessions vs
        ON vs.user_id=u.user_id AND vs.guild_id=u.guild_id AND vs.ended_at IS NOT NULL
      WHERE u.guild_id=$1
      GROUP BY u.user_id, u.nickname
      ORDER BY value_seconds DESC
      LIMIT 20
    `;
    const { rows } = await client.query(sql, [guildId.toString()]);
    return rows.map((r) => ({
      user_id: String(r.user_id),
      nickname: r.nickname ?? null,
      value_seconds: Number(r.value_seconds ?? 0),
    }));
  } finally {
    client.release();
  }
}

export type LevelBucket = { level: number; users: number };

export async function fetchLevelDistribution(guildId: bigint): Promise<LevelBucket[]> {
  const pool = getPool();
  const client = await pool.connect();
  try {
    const { rows } = await client.query(
      `
      SELECT level, COUNT(*)::int AS users
      FROM (
        SELECT CASE
          WHEN COALESCE(xp,0) < 100 THEN 0
          WHEN xp < 150 THEN 1
          WHEN xp < 250 THEN 2
          WHEN xp < 400 THEN 3
          WHEN xp < 600 THEN 4
          WHEN xp < 850 THEN 5
          WHEN xp < 1150 THEN 6
          WHEN xp < 1550 THEN 7
          WHEN xp < 2000 THEN 8
          ELSE 9
        END AS level
        FROM users WHERE guild_id=$1
      ) t
      GROUP BY level
      ORDER BY level
      `,
      [guildId.toString()]
    );
    return rows.map((r) => ({ level: Number(r.level), users: Number(r.users) }));
  } finally {
    client.release();
  }
}

export type SessionBucket = { bucket: string; count: number };

export async function fetchSessionLengthHistogram(
  guildId: bigint,
  days = 30
): Promise<SessionBucket[]> {
  const pool = getPool();
  const client = await pool.connect();
  try {
    const start = new Date();
    start.setDate(start.getDate() - days);
    const { rows } = await client.query(
      `
      WITH start_bound AS (
        SELECT ($2::timestamptz AT TIME ZONE 'Asia/Seoul') AS start_at
      )
      SELECT bucket, COUNT(*)::int AS count
      FROM (
        SELECT CASE
          WHEN duration_seconds < 300 THEN '0-5m'
          WHEN duration_seconds < 900 THEN '5-15m'
          WHEN duration_seconds < 1800 THEN '15-30m'
          WHEN duration_seconds < 3600 THEN '30-60m'
          WHEN duration_seconds < 7200 THEN '60-120m'
          ELSE '120m+'
        END AS bucket
        FROM voice_sessions
        WHERE guild_id=$1 AND ended_at IS NOT NULL
          AND (ended_at AT TIME ZONE 'Asia/Seoul') >= (SELECT start_at FROM start_bound)
      ) t
      GROUP BY bucket
      ORDER BY CASE bucket
        WHEN '0-5m' THEN 1
        WHEN '5-15m' THEN 2
        WHEN '15-30m' THEN 3
        WHEN '30-60m' THEN 4
        WHEN '60-120m' THEN 5
        ELSE 6 END
      `,
      [guildId.toString(), start]
    );
    return rows.map((r) => ({ bucket: String(r.bucket), count: Number(r.count) }));
  } finally {
    client.release();
  }
}


