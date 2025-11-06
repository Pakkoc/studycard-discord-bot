"""
Add test data for user 364764044948799491 in guild 132546567172054899
to test monthly color scheme in contribution calendar.

Generates random study sessions from 2025-01-01 to 2025-11-05.
"""
import asyncio
import os
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path
from dotenv import load_dotenv
from core.database import create_pool, close_pool, get_pool

# Load environment variables
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)


async def add_test_sessions(user_id: int, guild_id: int) -> None:
    """Add random test sessions for each day from Jan 1 to Nov 5, 2025."""
    pool = await get_pool()
    
    # Date range: 2025-01-01 to 2025-11-05
    start_date = datetime(2025, 1, 1, tzinfo=timezone.utc)
    end_date = datetime(2025, 11, 5, tzinfo=timezone.utc)
    
    current_date = start_date
    sessions_added = 0
    
    print(f"Adding test data for user {user_id} in guild {guild_id}")
    print(f"Date range: {start_date.date()} to {end_date.date()}")
    
    async with pool.acquire() as conn:
        async with conn.transaction():
            # Ensure user exists
            await conn.execute(
                """
                INSERT INTO users (user_id, guild_id, total_seconds, xp, last_seen_at)
                VALUES ($1, $2, 0, 0, NOW())
                ON CONFLICT (user_id, guild_id) DO NOTHING
                """,
                user_id,
                guild_id,
            )
            
            while current_date <= end_date:
                # 70% chance of having a study session on any given day
                if random.random() < 0.7:
                    # Random number of sessions per day (1-3)
                    num_sessions = random.randint(1, 3)
                    
                    for _ in range(num_sessions):
                        # Random start time during the day (6 AM to 10 PM)
                        hour = random.randint(6, 22)
                        minute = random.randint(0, 59)
                        
                        session_start = current_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
                        
                        # Random duration: 30 minutes to 4 hours
                        duration_seconds = random.randint(30 * 60, 4 * 60 * 60)
                        session_end = session_start + timedelta(seconds=duration_seconds)
                        
                        # Insert session
                        await conn.execute(
                            """
                            INSERT INTO voice_sessions (user_id, guild_id, started_at, ended_at, duration_seconds)
                            VALUES ($1, $2, $3, $4, $5)
                            """,
                            user_id,
                            guild_id,
                            session_start,
                            session_end,
                            duration_seconds,
                        )
                        
                        sessions_added += 1
                        
                        # Update user totals
                        await conn.execute(
                            """
                            UPDATE users 
                            SET total_seconds = COALESCE(total_seconds, 0) + $1,
                                xp = COALESCE(xp, 0) + $2,
                                last_seen_at = $3
                            WHERE user_id = $4 AND guild_id = $5
                            """,
                            duration_seconds,
                            duration_seconds // 3600,  # 1 XP per hour
                            session_end,
                            user_id,
                            guild_id,
                        )
                        
                        # Add daily streak
                        await conn.execute(
                            """
                            INSERT INTO daily_streaks (user_id, guild_id, streak_date)
                            VALUES ($1, $2, $3)
                            ON CONFLICT (user_id, guild_id, streak_date) DO NOTHING
                            """,
                            user_id,
                            guild_id,
                            current_date.date(),
                        )
                
                current_date += timedelta(days=1)
    
    print(f"✅ Successfully added {sessions_added} test sessions")
    
    # Show summary
    async with pool.acquire() as conn:
        summary = await conn.fetchrow(
            """
            SELECT 
                COUNT(*) as session_count,
                COALESCE(SUM(duration_seconds), 0) as total_seconds,
                COALESCE(SUM(duration_seconds), 0) / 3600.0 as total_hours
            FROM voice_sessions
            WHERE user_id = $1 AND guild_id = $2
            """,
            user_id,
            guild_id,
        )
        
        user_data = await conn.fetchrow(
            "SELECT total_seconds, xp FROM users WHERE user_id = $1 AND guild_id = $2",
            user_id,
            guild_id,
        )
        
        print(f"\n📊 Summary:")
        print(f"  Total sessions: {summary['session_count']}")
        print(f"  Total hours: {summary['total_hours']:.2f}")
        print(f"  User total_seconds: {user_data['total_seconds']}")
        print(f"  User XP: {user_data['xp']}")


async def main() -> None:
    user_id = 364764044948799491
    guild_id = 132546567172054899
    
    try:
        await create_pool()
        await add_test_sessions(user_id, guild_id)
    finally:
        await close_pool()


if __name__ == "__main__":
    asyncio.run(main())

