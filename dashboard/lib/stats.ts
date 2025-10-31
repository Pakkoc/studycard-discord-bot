import { getPool } from "@/lib/db";

export type GuildUserRow = {
  user_id: string; // serialized for JSON safety
  nickname: string | null;
  student_no: string | null;
  status: "active" | "left";
  level_name: string | null;
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
  | "status"
  | "level_name"
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

export type UserDetail = {
  user_id: string;
  nickname: string | null;
  student_no: string | null;
  status: "active" | "left";
  level_name: string | null;
  xp: number;
  total_seconds: number;
  last_seen_at: string | null;
};

export type UserEntryLog = {
  started_at: string;
  ended_at: string;
  duration_seconds: number;
};

export type UserDailyPoint = { date: string; hours: number };
export type UserMonthlyPoint = { month: string; hours: number };

export type HeatmapCell = { dow: number; hour: number; count: number; seconds: number };

export type CalendarDay = { date: string; seconds: number; sessions: number };
export type DayHourBin = { hour: number; seconds: number; sessions: number };
export type GuildCalendarDay = { date: string; seconds: number };

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
      WITH bounds AS (
        SELECT
          ((date_trunc('day', (now() AT TIME ZONE 'Asia/Seoul') - interval '6 hour') + interval '6 hour') AT TIME ZONE 'Asia/Seoul') AS today_start,
          ((date_trunc('week',  now() AT TIME ZONE 'Asia/Seoul')) AT TIME ZONE 'Asia/Seoul') AS week_start,
          ((date_trunc('month', now() AT TIME ZONE 'Asia/Seoul')) AT TIME ZONE 'Asia/Seoul') AS month_start
      )
      SELECT
        u.user_id,
        u.nickname,
        u.student_no,
        u.status,
        u.level_name,
        COALESCE(u.xp, 0) AS xp,
        COALESCE(u.total_seconds, 0) AS total_seconds,
        COALESCE(SUM(CASE WHEN vs.ended_at >= (SELECT today_start FROM bounds) THEN vs.duration_seconds END), 0) AS today_seconds,
        COALESCE(SUM(CASE WHEN vs.ended_at >= (SELECT week_start FROM bounds) THEN vs.duration_seconds END), 0) AS week_seconds,
        COALESCE(SUM(CASE WHEN vs.ended_at >= (SELECT month_start FROM bounds) THEN vs.duration_seconds END), 0) AS month_seconds,
        to_char(u.last_seen_at AT TIME ZONE 'Asia/Seoul', 'YYYY-MM-DD HH24:MI') AS last_seen_at
      FROM users u
      LEFT JOIN voice_sessions vs
        ON vs.user_id = u.user_id
       AND vs.guild_id = u.guild_id
       AND vs.ended_at IS NOT NULL
      WHERE u.guild_id = $1
      ${filterSql}
      GROUP BY u.user_id, u.nickname, u.student_no, u.status, u.level_name, u.xp, u.total_seconds, u.last_seen_at
      ORDER BY xp DESC, total_seconds DESC
      LIMIT $2
    `;

    const { rows } = await client.query(sql, params);

    return rows.map((r) => ({
      user_id: String(r.user_id),
      nickname: r.nickname ?? null,
      student_no: r.student_no ?? null,
      status: (r.status as string) === "left" ? "left" : "active",
      level_name: (r.level_name as string | null) ?? null,
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
      status: true,
      level_name: true,
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
      WITH bounds AS (
        SELECT
          ((date_trunc('day', (now() AT TIME ZONE 'Asia/Seoul') - interval '6 hour') + interval '6 hour') AT TIME ZONE 'Asia/Seoul') AS today_start,
          ((date_trunc('week',  now() AT TIME ZONE 'Asia/Seoul')) AT TIME ZONE 'Asia/Seoul') AS week_start,
          ((date_trunc('month', now() AT TIME ZONE 'Asia/Seoul')) AT TIME ZONE 'Asia/Seoul') AS month_start
      )
      SELECT
        u.user_id,
        u.nickname,
        u.student_no,
        u.status,
        u.level_name,
        COALESCE(u.xp, 0) AS xp,
        COALESCE(u.total_seconds, 0) AS total_seconds,
        COALESCE(SUM(CASE WHEN vs.ended_at >= (SELECT today_start FROM bounds) THEN vs.duration_seconds END), 0) AS today_seconds,
        COALESCE(SUM(CASE WHEN vs.ended_at >= (SELECT week_start FROM bounds) THEN vs.duration_seconds END), 0) AS week_seconds,
        COALESCE(SUM(CASE WHEN vs.ended_at >= (SELECT month_start FROM bounds) THEN vs.duration_seconds END), 0) AS month_seconds,
        to_char(u.last_seen_at AT TIME ZONE 'Asia/Seoul', 'YYYY-MM-DD HH24:MI') AS last_seen_at
      FROM users u
      LEFT JOIN voice_sessions vs
        ON vs.user_id = u.user_id
       AND vs.guild_id = u.guild_id
       AND vs.ended_at IS NOT NULL
      WHERE u.guild_id = $1
      ${query.length > 0 ? " AND (u.nickname ILIKE $2 OR u.student_no ILIKE $2 OR CAST(u.user_id AS TEXT) ILIKE $2) " : ""}
      GROUP BY u.user_id, u.nickname, u.student_no, u.status, u.level_name, u.xp, u.total_seconds, u.last_seen_at
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
        status: (r.status as string) === "left" ? "left" : "active",
        level_name: (r.level_name as string | null) ?? null,
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

export async function fetchUserDetail(guildId: bigint, userId: bigint): Promise<UserDetail | null> {
  const pool = getPool();
  const client = await pool.connect();
  try {
    const { rows } = await client.query(
      `
      SELECT u.user_id, u.nickname, u.student_no, u.status, u.level_name, COALESCE(u.xp,0) AS xp,
             COALESCE(u.total_seconds,0) AS total_seconds,
             to_char(u.last_seen_at AT TIME ZONE 'Asia/Seoul', 'YYYY-MM-DD HH24:MI') AS last_seen_at
      FROM users u
      WHERE u.guild_id=$1 AND u.user_id=$2
      `,
      [guildId.toString(), userId.toString()]
    );
    if (!rows[0]) return null;
    const r = rows[0];
    return {
      user_id: String(r.user_id),
      nickname: r.nickname ?? null,
      student_no: r.student_no ?? null,
      status: (r.status as string) === "left" ? "left" : "active",
      level_name: (r.level_name as string | null) ?? null,
      xp: Number(r.xp ?? 0),
      total_seconds: Number(r.total_seconds ?? 0),
      last_seen_at: (r.last_seen_at as string | null) ?? null,
    };
  } finally {
    client.release();
  }
}

export async function fetchUserEntryLogs(
  guildId: bigint,
  userId: bigint,
  limit = 100
): Promise<UserEntryLog[]> {
  const pool = getPool();
  const client = await pool.connect();
  try {
    const { rows } = await client.query(
      `
      SELECT to_char(started_at AT TIME ZONE 'Asia/Seoul', 'YYYY-MM-DD HH24:MI') AS started_at,
             to_char(ended_at   AT TIME ZONE 'Asia/Seoul', 'YYYY-MM-DD HH24:MI')   AS ended_at,
             duration_seconds
      FROM voice_sessions
      WHERE guild_id=$1 AND user_id=$2 AND ended_at IS NOT NULL
      ORDER BY ended_at DESC
      LIMIT $3
      `,
      [guildId.toString(), userId.toString(), limit]
    );
    return rows.map((r) => ({
      started_at: String(r.started_at),
      ended_at: String(r.ended_at),
      duration_seconds: Number(r.duration_seconds ?? 0),
    }));
  } finally {
    client.release();
  }
}

export async function fetchUserDailyTrend(
  guildId: bigint,
  userId: bigint,
  days = 30
): Promise<UserDailyPoint[]> {
  const pool = getPool();
  const client = await pool.connect();
  try {
    const start = new Date();
    start.setDate(start.getDate() - (days - 1));
    const { rows } = await client.query(
      `
      SELECT ((date_trunc('day', (ended_at AT TIME ZONE 'Asia/Seoul') - interval '6 hour') + interval '6 hour') AT TIME ZONE 'Asia/Seoul') AS d,
             SUM(duration_seconds) AS seconds
      FROM voice_sessions
      WHERE guild_id=$1 AND user_id=$2 AND ended_at IS NOT NULL AND ended_at >= $3
      GROUP BY d
      ORDER BY d
      `,
      [guildId.toString(), userId.toString(), start]
    );
    const map = new Map<string, number>();
    for (const r of rows) {
      const d = new Date(r.d).toISOString().slice(0, 10);
      map.set(d, Number(r.seconds ?? 0));
    }
    const out: UserDailyPoint[] = [];
    for (let i = 0; i < days; i++) {
      const d = new Date(start);
      d.setDate(start.getDate() + i);
      const key = d.toISOString().slice(0, 10);
      const seconds = map.get(key) ?? 0;
      out.push({ date: key, hours: Math.round((seconds / 3600) * 100) / 100 });
    }
    return out;
  } finally {
    client.release();
  }
}

export async function fetchUserWeekdayHourHeatmap(
  guildId: bigint,
  userId: bigint,
  days = 90
): Promise<HeatmapCell[]> {
  const pool = getPool();
  const client = await pool.connect();
  try {
    const start = new Date();
    start.setDate(start.getDate() - days);
    const { rows } = await client.query(
      `
      SELECT EXTRACT(DOW FROM ended_at AT TIME ZONE 'Asia/Seoul')::int AS dow,
             EXTRACT(HOUR FROM ended_at AT TIME ZONE 'Asia/Seoul')::int AS hour,
             COUNT(*)::int AS cnt,
             COALESCE(SUM(duration_seconds), 0) AS seconds
      FROM voice_sessions
      WHERE guild_id=$1 AND user_id=$2 AND ended_at IS NOT NULL AND ended_at >= $3
      GROUP BY dow, hour
      ORDER BY dow, hour
      `,
      [guildId.toString(), userId.toString(), start]
    );
    return rows.map((r) => ({ dow: Number(r.dow), hour: Number(r.hour), count: Number(r.cnt), seconds: Number(r.seconds || 0) }));
  } finally {
    client.release();
  }
}

export async function fetchUserMonthlyTrend(
  guildId: bigint,
  userId: bigint,
  months = 12
): Promise<UserMonthlyPoint[]> {
  const pool = getPool();
  const client = await pool.connect();
  try {
    // Start from first day of (months-1) months ago
    const start = new Date();
    start.setUTCDate(1);
    start.setUTCMonth(start.getUTCMonth() - (months - 1));
    const end = new Date();
    const { rows } = await client.query(
      `
      WITH month_bounds AS (
        SELECT
          date_trunc('month', $3::timestamptz AT TIME ZONE 'Asia/Seoul') AS start_month,
          date_trunc('month', $4::timestamptz AT TIME ZONE 'Asia/Seoul') AS end_month
      ), months AS (
        SELECT generate_series(
          (SELECT start_month FROM month_bounds),
          (SELECT end_month   FROM month_bounds),
          interval '1 month'
        ) AS m
      ), agg AS (
        SELECT date_trunc('month', ended_at AT TIME ZONE 'Asia/Seoul') AS m,
               SUM(duration_seconds) AS seconds
        FROM voice_sessions
        WHERE guild_id=$1 AND user_id=$2 AND ended_at IS NOT NULL
          AND (ended_at AT TIME ZONE 'Asia/Seoul') >= (SELECT start_month FROM month_bounds)
          AND (ended_at AT TIME ZONE 'Asia/Seoul') <  ((SELECT end_month FROM month_bounds) + interval '1 month')
        GROUP BY m
      )
      SELECT to_char(months.m, 'YYYY-MM') AS month,
             COALESCE(agg.seconds, 0) AS seconds
      FROM months
      LEFT JOIN agg ON agg.m = months.m
      ORDER BY months.m
      `,
      [guildId.toString(), userId.toString(), start, end]
    );
    return rows.map((r) => ({ month: String(r.month), hours: Math.round(((Number(r.seconds || 0) / 3600)) * 100) / 100 }));
  } finally {
    client.release();
  }
}

export async function fetchUserCalendarYear(
  guildId: bigint,
  userId: bigint,
  year: number
): Promise<CalendarDay[]> {
  const pool = getPool();
  const client = await pool.connect();
  try {
    const start = new Date(Date.UTC(year, 0, 1));
    const end = new Date(Date.UTC(year + 1, 0, 1));
    const { rows } = await client.query(
      `
      WITH bounds AS (
        SELECT 
          -- Use timestamp without time zone in KST to align with daily_agg.d type
          (date_trunc('day', $3::timestamptz AT TIME ZONE 'Asia/Seoul') + interval '6 hour') AS s,
          (date_trunc('day', $4::timestamptz AT TIME ZONE 'Asia/Seoul') + interval '6 hour') AS e
      ), sessions_kst AS (
        SELECT 
          started_at AT TIME ZONE 'Asia/Seoul' AS start_kst,
          ended_at AT TIME ZONE 'Asia/Seoul' AS end_kst,
          session_id
        FROM voice_sessions
        WHERE guild_id=$1 AND user_id=$2 
          AND ended_at IS NOT NULL 
          AND ended_at >= (SELECT s FROM bounds) 
          AND started_at < (SELECT e FROM bounds)
      ), split_by_date AS (
        SELECT 
          session_id,
          -- Calculate which dates this session spans
          generate_series(
            (date_trunc('day', start_kst - interval '6 hour') + interval '6 hour'),
            (date_trunc('day', end_kst - interval '6 hour') + interval '6 hour'),
            interval '1 day'
          ) AS date_boundary
        FROM sessions_kst
      ), daily_split AS (
        SELECT 
          sd.session_id,
          sd.date_boundary AS d,
          -- Calculate seconds for this date portion: intersection of session time and date boundary
          EXTRACT(EPOCH FROM (
            LEAST(sk.end_kst, sd.date_boundary + interval '1 day') - 
            GREATEST(sk.start_kst, sd.date_boundary)
          ))::bigint AS seconds
        FROM split_by_date sd
        JOIN sessions_kst sk ON sd.session_id = sk.session_id
        WHERE sk.end_kst > sd.date_boundary AND sk.start_kst < sd.date_boundary + interval '1 day'
      ), daily_agg AS (
        SELECT 
          d,
          SUM(seconds)::bigint AS seconds,
          COUNT(DISTINCT session_id) AS sessions
        FROM daily_split
        WHERE seconds > 0
        GROUP BY d
      ), days AS (
        SELECT generate_series((SELECT s FROM bounds), (SELECT e FROM bounds) - interval '1 day', interval '1 day') AS d
      )
      SELECT to_char(days.d, 'YYYY-MM-DD') AS date,
             COALESCE(daily_agg.seconds, 0) AS seconds,
             COALESCE(daily_agg.sessions, 0) AS sessions
      FROM days
      LEFT JOIN daily_agg ON days.d = daily_agg.d
      ORDER BY days.d
      `,
      [guildId.toString(), userId.toString(), start, end]
    );
    return rows.map((r) => ({ date: String(r.date), seconds: Number(r.seconds || 0), sessions: Number(r.sessions || 0) }));
  } catch (error) {
    console.error('Error in fetchUserCalendarYear:', error);
    // Return empty array instead of throwing to prevent UI crash
    return [];
  } finally {
    client.release();
  }
}

export async function fetchGuildCalendarYear(
  guildId: bigint,
  year: number
): Promise<GuildCalendarDay[]> {
  const pool = getPool();
  const client = await pool.connect();
  try {
    const start = new Date(Date.UTC(year, 0, 1));
    const end = new Date(Date.UTC(year + 1, 0, 1));
    const { rows } = await client.query(
      `
      WITH day_bounds AS (
        SELECT
          date_trunc('day', $2::timestamptz AT TIME ZONE 'Asia/Seoul') AS start_day,
          date_trunc('day', $3::timestamptz AT TIME ZONE 'Asia/Seoul') AS end_day
      ), days AS (
        SELECT generate_series(
          (SELECT start_day FROM day_bounds),
          (SELECT end_day FROM day_bounds) - interval '1 day',
          interval '1 day'
        ) AS d
      ), daily AS (
        SELECT date_trunc('day', ended_at AT TIME ZONE 'Asia/Seoul') AS d,
               SUM(duration_seconds) AS seconds
        FROM voice_sessions
        WHERE guild_id=$1 AND ended_at IS NOT NULL
          AND (ended_at AT TIME ZONE 'Asia/Seoul') >= (SELECT start_day FROM day_bounds)
          AND (ended_at AT TIME ZONE 'Asia/Seoul') <  ((SELECT end_day FROM day_bounds) + interval '1 day')
        GROUP BY d
      )
      SELECT to_char(days.d, 'YYYY-MM-DD') AS date,
             COALESCE(daily.seconds, 0) AS seconds
      FROM days
      LEFT JOIN daily ON daily.d = days.d
      ORDER BY days.d
      `,
      [guildId.toString(), start, end]
    );
    return rows.map((r) => ({ date: String(r.date), seconds: Number(r.seconds || 0) }));
  } finally {
    client.release();
  }
}

// 길드 전체에서 "개인별 하루 총합"의 최대치를 구함 (연간 범위)
// Sessions spanning multiple days are split by date boundary (06:00 KST).
export async function fetchGuildPerUserDailyMaxHours(
  guildId: bigint,
  year: number
): Promise<number> {
  const pool = getPool();
  const client = await pool.connect();
  try {
    const start = new Date(Date.UTC(year, 0, 1));
    const end = new Date(Date.UTC(year + 1, 0, 1));
    const { rows } = await client.query(
      `
      WITH bounds AS (
        SELECT 
          ((date_trunc('day', $2::timestamptz AT TIME ZONE 'Asia/Seoul') + interval '6 hour') AT TIME ZONE 'Asia/Seoul') AS s,
          ((date_trunc('day', $3::timestamptz AT TIME ZONE 'Asia/Seoul') + interval '6 hour') AT TIME ZONE 'Asia/Seoul') AS e
      ), sessions_kst AS (
        SELECT 
          user_id,
          started_at AT TIME ZONE 'Asia/Seoul' AS start_kst,
          ended_at AT TIME ZONE 'Asia/Seoul' AS end_kst,
          session_id
        FROM voice_sessions
        WHERE guild_id=$1 
          AND ended_at IS NOT NULL 
          AND ended_at >= (SELECT s FROM bounds) 
          AND started_at < (SELECT e FROM bounds)
      ), split_by_date AS (
        SELECT 
          user_id,
          session_id,
          -- Calculate which dates this session spans
          generate_series(
            (date_trunc('day', start_kst - interval '6 hour') + interval '6 hour'),
            (date_trunc('day', end_kst - interval '6 hour') + interval '6 hour'),
            interval '1 day'
          ) AS date_boundary
        FROM sessions_kst
      ), daily_split AS (
        SELECT 
          sd.user_id,
          sd.date_boundary AS d,
          -- Calculate seconds for this date portion: intersection of session time and date boundary
          EXTRACT(EPOCH FROM (
            LEAST(sk.end_kst, sd.date_boundary + interval '1 day') - 
            GREATEST(sk.start_kst, sd.date_boundary)
          ))::bigint AS seconds
        FROM split_by_date sd
        JOIN sessions_kst sk ON sd.session_id = sk.session_id AND sd.user_id = sk.user_id
        WHERE sk.end_kst > sd.date_boundary AND sk.start_kst < sd.date_boundary + interval '1 day'
      ), daily AS (
        SELECT user_id,
               d,
               SUM(seconds)::bigint AS seconds
        FROM daily_split
        WHERE seconds > 0
        GROUP BY user_id, d
      )
      SELECT COALESCE(MAX(seconds), 0) AS max_seconds
      FROM daily
      `,
      [guildId.toString(), start, end]
    );
    const maxSeconds = Number(rows?.[0]?.max_seconds ?? 0);
    const hours = Math.round(((maxSeconds / 3600)) * 100) / 100;
    return hours;
  } catch (error) {
    console.error('Error in fetchGuildPerUserDailyMaxHours:', error);
    // Return 0 instead of throwing to prevent UI crash
    return 0;
  } finally {
    client.release();
  }
}

export async function fetchUserDayHours(
  guildId: bigint,
  userId: bigint,
  date: string // 'YYYY-MM-DD'
): Promise<DayHourBin[]> {
  const pool = getPool();
  const client = await pool.connect();
  try {
    const { rows } = await client.query(
      `
      WITH day_bounds AS (
        SELECT 
          ((to_timestamp($3, 'YYYY-MM-DD') AT TIME ZONE 'Asia/Seoul') + interval '6 hour') AT TIME ZONE 'Asia/Seoul' AS s,
          (((to_timestamp($3, 'YYYY-MM-DD') + interval '1 day') AT TIME ZONE 'Asia/Seoul') + interval '6 hour') AT TIME ZONE 'Asia/Seoul' AS e
      )
      SELECT EXTRACT(HOUR FROM ended_at AT TIME ZONE 'Asia/Seoul')::int AS hour,
             COALESCE(SUM(duration_seconds), 0) AS seconds,
             COUNT(*) AS sessions
      FROM voice_sessions
      WHERE guild_id=$1 AND user_id=$2 AND ended_at IS NOT NULL
        AND ended_at >= (SELECT s FROM day_bounds) AND ended_at < (SELECT e FROM day_bounds)
      GROUP BY hour
      ORDER BY hour
      `,
      [guildId.toString(), userId.toString(), date]
    );
    const map = new Map<number, { seconds: number; sessions: number }>();
    for (const r of rows) {
      map.set(Number(r.hour), { seconds: Number(r.seconds || 0), sessions: Number(r.sessions || 0) });
    }
    const out: DayHourBin[] = [];
    for (let h = 0; h < 24; h++) {
      const v = map.get(h) || { seconds: 0, sessions: 0 };
      out.push({ hour: h, seconds: v.seconds, sessions: v.sessions });
    }
    return out;
  } finally {
    client.release();
  }
}

export async function fetchUserAvailableYears(
  guildId: bigint,
  userId: bigint
): Promise<number[]> {
  const pool = getPool();
  const client = await pool.connect();
  try {
    const { rows } = await client.query(
      `
      SELECT DISTINCT EXTRACT(YEAR FROM ended_at AT TIME ZONE 'Asia/Seoul')::int AS year
      FROM voice_sessions
      WHERE guild_id=$1 AND user_id=$2 AND ended_at IS NOT NULL
      ORDER BY year
      `,
      [guildId.toString(), userId.toString()]
    );
    return rows.map((r) => Number(r.year)).filter((y) => Number.isFinite(y));
  } finally {
    client.release();
  }
}


