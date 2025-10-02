import asyncio
import os
from datetime import date, datetime, timezone, timedelta
from typing import Optional, Dict

import asyncpg


_pool: Optional[asyncpg.Pool] = None


def get_database_url() -> str:
    database_url = os.getenv("DATABASE_URL", "").strip()
    if not database_url:
        # Example: postgresql://user:password@host:5432/dbname
        raise RuntimeError(
            "DATABASE_URL is not set. Please set it in your .env (e.g., postgresql://user:pass@host:5432/db)"
        )
    return database_url


async def create_pool(min_size: int = 1, max_size: int = 5) -> asyncpg.Pool:
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(dsn=get_database_url(), min_size=min_size, max_size=max_size)
    return _pool


async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        _pool = await create_pool()
    return _pool


async def close_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


async def test_connection() -> int:
    pool = await get_pool()
    async with pool.acquire() as conn:
        value = await conn.fetchval("SELECT 1;")
        return int(value)


async def execute_sql_file(path: str) -> None:
    """Execute a .sql file contents as a single script.

    The script should be idempotent (use IF NOT EXISTS where appropriate).
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        with open(path, "r", encoding="utf-8") as f:
            sql = f.read()
        # asyncpg does not support multiple statements with parameters in one call,
        # but simple EXECUTE for our migration text is fine.
        await conn.execute(sql)


async def ensure_user_exists(conn: asyncpg.Connection, user_id: int, guild_id: int) -> None:
    await conn.execute(
        """
        INSERT INTO users (user_id, guild_id, status)
        VALUES ($1, $2, 'active')
        ON CONFLICT (user_id, guild_id) DO NOTHING;
        """,
        user_id,
        guild_id,
    )


async def set_user_nickname(user_id: int, guild_id: int, nickname: str) -> None:
    """Upsert nickname for a user."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await ensure_user_exists(conn, user_id, guild_id)
        await conn.execute(
            """
            UPDATE users
            SET nickname=$1
            WHERE user_id=$2 AND guild_id=$3
            """,
            nickname,
            user_id,
            guild_id,
        )


async def set_user_nicknames(guild_id: int, user_id_to_nick: Dict[int, str]) -> None:
    """Upsert nicknames for many users at once.

    Uses INSERT ... ON CONFLICT DO UPDATE to ensure rows exist and nicknames are stored.
    """
    if not user_id_to_nick:
        return
    pool = await get_pool()
    async with pool.acquire() as conn:
        records = [(uid, guild_id, nick) for uid, nick in user_id_to_nick.items()]
        await conn.executemany(
            """
            INSERT INTO users (user_id, guild_id, nickname)
            VALUES ($1, $2, $3)
            ON CONFLICT (user_id, guild_id) DO UPDATE SET nickname=EXCLUDED.nickname
            """,
            records,
        )


async def set_user_student_no(user_id: int, guild_id: int, student_no: str) -> None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        await ensure_user_exists(conn, user_id, guild_id)
        await conn.execute(
            """
            UPDATE users
            SET student_no=$1
            WHERE user_id=$2 AND guild_id=$3
            """,
            student_no,
            user_id,
            guild_id,
        )


async def set_user_student_nos(guild_id: int, user_id_to_stuno: Dict[int, str]) -> None:
    if not user_id_to_stuno:
        return
    pool = await get_pool()
    async with pool.acquire() as conn:
        records = [(uid, guild_id, st) for uid, st in user_id_to_stuno.items()]
        await conn.executemany(
            """
            INSERT INTO users (user_id, guild_id, student_no)
            VALUES ($1, $2, $3)
            ON CONFLICT (user_id, guild_id) DO UPDATE SET student_no=EXCLUDED.student_no
            """,
            records,
        )


async def ensure_user(user_id: int, guild_id: int) -> None:
    """Ensure a single user record exists (opens its own connection)."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await ensure_user_exists(conn, user_id, guild_id)


async def ensure_users_for_guild(guild_id: int, user_ids: list[int]) -> None:
    """Bulk upsert users for a guild. Safe to call repeatedly.

    Uses executemany with ON CONFLICT DO NOTHING for efficiency.
    """
    if not user_ids:
        return
    pool = await get_pool()
    async with pool.acquire() as conn:
        records = [(uid, guild_id) for uid in user_ids]
        await conn.executemany(
            """
            INSERT INTO users (user_id, guild_id, status)
            VALUES ($1, $2, 'active')
            ON CONFLICT (user_id, guild_id) DO NOTHING;
            """,
            records,
        )


async def purge_user_non_session_data(user_id: int, guild_id: int) -> None:
    """Remove non-session data for a user while keeping voice_sessions.

    - Deletes daily_streaks rows
    - Resets users.xp and users.total_seconds to 0 and clears last_seen_at
    Note: We deliberately DO NOT delete from users because voice_sessions
    has a FK that would cascade.
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute(
                "DELETE FROM daily_streaks WHERE user_id=$1 AND guild_id=$2",
                user_id,
                guild_id,
            )
            # user_achievements table removed – no longer deleting from it
            await conn.execute(
                """
                UPDATE users
                SET xp=0, total_seconds=0, last_seen_at=NULL
                WHERE user_id=$1 AND guild_id=$2
                """,
                user_id,
                guild_id,
            )


async def record_voice_session(
    user_id: int,
    guild_id: int,
    started_at: datetime,
    ended_at: datetime,
    duration_seconds: int,
) -> Dict[str, int]:
    """Insert a finished voice session and update aggregates in a transaction.

    Returns a dict with keys: xp_gain, total_xp, old_level, new_level
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            await ensure_user_exists(conn, user_id, guild_id)

            # Insert session regardless of duration (already filtered by caller when needed)
            await conn.execute(
                """
                INSERT INTO voice_sessions (user_id, guild_id, started_at, ended_at, duration_seconds)
                VALUES ($1, $2, $3, $4, $5);
                """,
                user_id,
                guild_id,
                started_at,
                ended_at,
                duration_seconds,
            )

            # Fetch previous aggregates for cumulative-based XP calculation
            from core.leveling import calculate_level, calculate_cumulative_xp_gain

            prev_row = await conn.fetchrow(
                """
                SELECT COALESCE(total_seconds,0) AS total_seconds,
                       COALESCE(xp,0) AS xp
                FROM users
                WHERE user_id=$1 AND guild_id=$2
                FOR UPDATE
                """,
                user_id,
                guild_id,
            )
            prev_total_seconds = int(prev_row["total_seconds"]) if prev_row else 0
            old_total_xp = int(prev_row["xp"]) if prev_row else 0
            old_level = calculate_level(old_total_xp)

            # Update aggregates (seconds)
            new_total_seconds_row = await conn.fetchrow(
                """
                UPDATE users
                SET total_seconds = COALESCE(total_seconds, 0) + $1,
                    last_seen_at = $2
                WHERE user_id = $3 AND guild_id = $4
                RETURNING total_seconds
                """,
                duration_seconds,
                ended_at,
                user_id,
                guild_id,
            )
            new_total_seconds = int(new_total_seconds_row["total_seconds"]) if new_total_seconds_row else prev_total_seconds + duration_seconds

            # Cumulative-based XP: compute increments across boundary crossings using previous total
            delta_seconds = max(0, new_total_seconds - prev_total_seconds)
            xp_gain = calculate_cumulative_xp_gain(prev_total_seconds, delta_seconds)

            if xp_gain > 0:
                updated_xp_row = await conn.fetchrow(
                    """
                    UPDATE users
                    SET xp = COALESCE(xp,0) + $1
                    WHERE user_id=$2 AND guild_id=$3
                    RETURNING xp
                    """,
                    xp_gain,
                    user_id,
                    guild_id,
                )
                total_xp = int(updated_xp_row["xp"]) if updated_xp_row else old_total_xp
            else:
                total_xp = old_total_xp

            new_level = calculate_level(total_xp)

            streak_day: date = ended_at.astimezone(timezone.utc).date()
            await conn.execute(
                """
                INSERT INTO daily_streaks (user_id, guild_id, streak_date)
                VALUES ($1, $2, $3)
                ON CONFLICT (user_id, guild_id, streak_date) DO NOTHING;
                """,
                user_id,
                guild_id,
                streak_day,
            )

            # Persist computed level and level_name for convenience
            from core.leveling import get_level_title as _ltitle
            await conn.execute(
                "UPDATE users SET level=$1, level_name=$2 WHERE user_id=$3 AND guild_id=$4",
                int(new_level),
                _ltitle(int(new_level)),
                user_id,
                guild_id,
            )
            return {
                "xp_gain": int(xp_gain),
                "total_xp": int(total_xp),
                "old_level": int(old_level),
                "new_level": int(new_level),
            }


async def add_xp(user_id: int, guild_id: int, delta_xp: int) -> Dict[str, int]:
    """Atomically add XP to a user and return level transition info.

    Returns dict keys: xp_gain, total_xp, old_level, new_level
    """
    if delta_xp == 0:
        return {"xp_gain": 0, "total_xp": 0, "old_level": 0, "new_level": 0}

    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            # Ensure user exists
            await ensure_user_exists(conn, user_id, guild_id)

            # Get current XP
            row = await conn.fetchrow(
                "SELECT COALESCE(xp,0) AS xp FROM users WHERE user_id=$1 AND guild_id=$2",
                user_id,
                guild_id,
            )
            current_xp = int(row["xp"]) if row else 0

            from core.leveling import calculate_level

            old_level = calculate_level(current_xp)
            new_total = max(0, current_xp + int(delta_xp))

            updated = await conn.fetchrow(
                """
                UPDATE users
                SET xp=$1, last_seen_at=NOW()
                WHERE user_id=$2 AND guild_id=$3
                RETURNING xp
                """,
                new_total,
                user_id,
                guild_id,
            )
            total_xp = int(updated["xp"]) if updated else new_total
            new_level = calculate_level(total_xp)
            # Persist level and level_name
            from core.leveling import get_level_title as _ltitle2
            await conn.execute(
                "UPDATE users SET level=$1, level_name=$2 WHERE user_id=$3 AND guild_id=$4",
                int(new_level),
                _ltitle2(int(new_level)),
                user_id,
                guild_id,
            )

            return {
                "xp_gain": int(delta_xp),
                "total_xp": int(total_xp),
                "old_level": int(old_level),
                "new_level": int(new_level),
            }

async def fetch_user_stats(user_id: int, guild_id: int) -> Optional[Dict[str, int]]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT
                COALESCE(u.total_seconds,0) AS total_seconds,
                COALESCE(u.xp,0) AS xp,
                COALESCE(u.student_no, '') AS student_no,
                COALESCE(SUM(CASE WHEN vs.ended_at >= date_trunc('day',   now()) THEN vs.duration_seconds END), 0) AS today_seconds,
                COALESCE(SUM(CASE WHEN vs.ended_at >= date_trunc('week',  now()) THEN vs.duration_seconds END), 0) AS week_seconds,
                COALESCE(SUM(CASE WHEN vs.ended_at >= date_trunc('month', now()) THEN vs.duration_seconds END), 0) AS month_seconds
            FROM users u
            LEFT JOIN voice_sessions vs
                ON vs.user_id=u.user_id AND vs.guild_id=u.guild_id AND vs.ended_at IS NOT NULL
            WHERE u.user_id=$1 AND u.guild_id=$2
            GROUP BY u.total_seconds, u.xp, u.student_no
            """,
            user_id,
            guild_id,
        )
        if not row:
            return None
        return {
            "total_seconds": int(row["total_seconds"]),
            "xp": int(row["xp"]),
            "student_no": str(row["student_no"]) if row["student_no"] is not None else "",
            "today_seconds": int(row["today_seconds"]),
            "week_seconds": int(row["week_seconds"]),
            "month_seconds": int(row["month_seconds"]),
        }


async def fetch_recent_streak_days(user_id: int, guild_id: int, days: int = 35) -> Dict[str, set]:
    """Return a set of dates (UTC ISO strings) for which user has entries in daily_streaks over last N days.

    Also returns today's date string for convenience.
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT streak_date
            FROM daily_streaks
            WHERE user_id=$1 AND guild_id=$2 AND streak_date >= (CURRENT_DATE - $3::int)
            """,
            user_id,
            guild_id,
            days,
        )
        played = {r["streak_date"].isoformat() for r in rows}
        return {"played": played, "today": date.today().isoformat()}


async def fetch_month_streak_days(user_id: int, guild_id: int, year: int | None = None, month: int | None = None) -> Dict[str, object]:
    """Return set of day numbers for current (or given) month where user has streak entries.

    Also returns (year, month, today_day).
    """
    today = date.today()
    y = year or today.year
    m = month or today.month
    # compute first and last day dates
    import calendar as _calendar
    num_days = _calendar.monthrange(y, m)[1]
    first = date(y, m, 1)
    last = date(y, m, num_days)
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT streak_date FROM daily_streaks
            WHERE user_id=$1 AND guild_id=$2 AND streak_date BETWEEN $3 AND $4
            """,
            user_id,
            guild_id,
            first,
            last,
        )
        days_played = {int(r["streak_date"].day) for r in rows}
        return {"year": y, "month": m, "days": days_played, "today": today.day if (today.year==y and today.month==m) else None}


async def finalize_open_sessions(min_duration_seconds: int) -> int:
    """Finalize sessions with NULL ended_at by setting ended_at=NOW() and duration.

    Sessions shorter than the provided threshold will be finalized but not
    added to users.total_seconds nor daily_streaks.
    Returns the number of sessions finalized.
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            # Fetch open sessions
            open_sessions = await conn.fetch(
                "SELECT session_id, user_id, guild_id, started_at FROM voice_sessions WHERE ended_at IS NULL"
            )
            if not open_sessions:
                return 0

            now = datetime.now(timezone.utc)
            finalized_count = 0
            for rec in open_sessions:
                session_id = rec["session_id"]
                user_id = rec["user_id"]
                guild_id = rec["guild_id"]
                started_at: datetime = rec["started_at"]
                duration = int((now - started_at).total_seconds())

                await conn.execute(
                    "UPDATE voice_sessions SET ended_at=$1, duration_seconds=$2 WHERE session_id=$3",
                    now,
                    duration,
                    session_id,
                )

                if duration >= min_duration_seconds:
                    # Fetch previous totals for cumulative XP
                    from core.leveling import calculate_level, calculate_cumulative_xp_gain

                    prev_row = await conn.fetchrow(
                        "SELECT COALESCE(total_seconds,0) AS total_seconds, COALESCE(xp,0) AS xp FROM users WHERE user_id=$1 AND guild_id=$2 FOR UPDATE",
                        user_id,
                        guild_id,
                    )
                    prev_total_seconds = int(prev_row["total_seconds"]) if prev_row else 0
                    old_total_xp = int(prev_row["xp"]) if prev_row else 0

                    # Update aggregates
                    updated_row = await conn.fetchrow(
                        """
                        UPDATE users SET total_seconds = COALESCE(total_seconds,0) + $1, last_seen_at=$2
                        WHERE user_id=$3 AND guild_id=$4
                        RETURNING total_seconds
                        """,
                        duration,
                        now,
                        user_id,
                        guild_id,
                    )
                    new_total_seconds = int(updated_row["total_seconds"]) if updated_row else prev_total_seconds + duration

                    # Cumulative XP based on boundary crossings
                    delta_seconds = max(0, new_total_seconds - prev_total_seconds)
                    xp_gain = calculate_cumulative_xp_gain(prev_total_seconds, delta_seconds)
                    if xp_gain > 0:
                        await conn.execute(
                            "UPDATE users SET xp = COALESCE(xp,0) + $1 WHERE user_id=$2 AND guild_id=$3",
                            xp_gain,
                            user_id,
                            guild_id,
                        )
                        # Update level after XP change
                        row2 = await conn.fetchrow(
                            "SELECT COALESCE(xp,0) AS xp FROM users WHERE user_id=$1 AND guild_id=$2",
                            user_id,
                            guild_id,
                        )
                        total_xp2 = int(row2["xp"]) if row2 else 0
                        from core.leveling import calculate_level as _calc
                        lvl2 = _calc(total_xp2)
                        from core.leveling import get_level_title as _ltitle3
                        await conn.execute(
                            "UPDATE users SET level=$1, level_name=$2 WHERE user_id=$3 AND guild_id=$4",
                            int(lvl2),
                            _ltitle3(int(lvl2)),
                            user_id,
                            guild_id,
                        )

                    # streak
                    streak_day: date = now.date()
                    await conn.execute(
                        """
                        INSERT INTO daily_streaks (user_id, guild_id, streak_date)
                        VALUES ($1, $2, $3)
                        ON CONFLICT (user_id, guild_id, streak_date) DO NOTHING;
                        """,
                        user_id,
                        guild_id,
                        streak_day,
                    )

                finalized_count += 1

            return finalized_count


async def main() -> None:
    try:
        result = await test_connection()
        print(f"DB connection OK, SELECT 1 -> {result}")
    except Exception as exc:
        print(f"DB connection FAILED: {exc}")
    finally:
        await close_pool()


if __name__ == "__main__":
    asyncio.run(main())


