"""
과거 채팅 메시지를 조회하여 chat_activity 테이블에 백필하는 스크립트.

사용법:
  python scripts/backfill_chat_activity.py [--days 30]

옵션:
  --days: 며칠 전까지 조회할지 (기본값: 30)
"""

import asyncio
import argparse
import logging
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Add project root to path
repo_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repo_root))

from dotenv import load_dotenv
load_dotenv()

import discord
import asyncpg

# 한국 시간대 (KST, UTC+9)
KST = timezone(timedelta(hours=9))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


async def get_pool() -> asyncpg.Pool:
    database_url = os.getenv("DATABASE_URL", "").strip()
    if not database_url:
        raise RuntimeError("DATABASE_URL is not set")
    return await asyncpg.create_pool(dsn=database_url, min_size=1, max_size=5)


async def record_chat_activity_batch(pool: asyncpg.Pool, records: list[tuple[int, int, datetime]]) -> int:
    """Batch insert chat activity records. Returns number of new records inserted."""
    if not records:
        return 0

    async with pool.acquire() as conn:
        # Convert to date and deduplicate
        date_records = list(set((uid, gid, dt.date()) for uid, gid, dt in records))

        inserted = 0
        for user_id, guild_id, activity_date in date_records:
            result = await conn.execute(
                """
                INSERT INTO chat_activity (user_id, guild_id, activity_date)
                VALUES ($1, $2, $3)
                ON CONFLICT (user_id, guild_id, activity_date) DO NOTHING
                """,
                user_id,
                guild_id,
                activity_date,
            )
            if result == "INSERT 0 1":
                inserted += 1
        return inserted


async def backfill_channel(
    channel: discord.TextChannel,
    pool: asyncpg.Pool,
    after_date: datetime,
    guild_id: int,
) -> int:
    """Backfill chat activity from a single channel. Returns count of new records."""
    total_inserted = 0
    batch: list[tuple[int, int, datetime]] = []
    batch_size = 100
    message_count = 0

    try:
        async for message in channel.history(limit=None, after=after_date, oldest_first=True):
            if message.author.bot:
                continue

            # Convert to KST
            created_kst = message.created_at.astimezone(KST).replace(tzinfo=None)
            batch.append((message.author.id, guild_id, created_kst))
            message_count += 1

            if len(batch) >= batch_size:
                inserted = await record_chat_activity_batch(pool, batch)
                total_inserted += inserted
                batch.clear()

        # Process remaining batch
        if batch:
            inserted = await record_chat_activity_batch(pool, batch)
            total_inserted += inserted

        logger.info(f"  #{channel.name}: {message_count} messages, {total_inserted} new records")

    except discord.Forbidden:
        logger.warning(f"  #{channel.name}: 접근 권한 없음 (스킵)")
    except Exception as e:
        logger.error(f"  #{channel.name}: 오류 발생 - {e}")

    return total_inserted


async def backfill_guild(
    guild: discord.Guild,
    pool: asyncpg.Pool,
    days: int,
) -> int:
    """Backfill chat activity for all channels in a guild."""
    after_date = datetime.now(timezone.utc) - timedelta(days=days)
    total_inserted = 0

    logger.info(f"길드 '{guild.name}' (ID: {guild.id}) 백필 시작...")
    logger.info(f"  조회 기간: {days}일 전부터 현재까지")

    # Get all text channels
    text_channels = [ch for ch in guild.channels if isinstance(ch, discord.TextChannel)]
    logger.info(f"  텍스트 채널 수: {len(text_channels)}")

    for channel in text_channels:
        inserted = await backfill_channel(channel, pool, after_date, guild.id)
        total_inserted += inserted
        # Small delay to avoid rate limiting
        await asyncio.sleep(0.5)

    # Also check threads in forums
    for channel in guild.channels:
        if isinstance(channel, discord.ForumChannel):
            logger.info(f"  포럼 '{channel.name}' 스레드 조회 중...")
            try:
                threads = channel.threads
                for thread in threads:
                    inserted = await backfill_channel(thread, pool, after_date, guild.id)
                    total_inserted += inserted
                    await asyncio.sleep(0.5)
            except Exception as e:
                logger.warning(f"  포럼 '{channel.name}' 스레드 조회 실패: {e}")

    logger.info(f"길드 '{guild.name}' 완료: 총 {total_inserted}개 새 레코드")
    return total_inserted


async def main(days: int):
    token = os.getenv("DISCORD_BOT_TOKEN", "")
    if not token:
        logger.error("DISCORD_BOT_TOKEN이 설정되지 않았습니다.")
        return

    # Create database pool
    pool = await get_pool()
    logger.info("데이터베이스 연결 완료")

    # Create Discord client
    intents = discord.Intents.default()
    intents.message_content = True
    intents.members = True

    client = discord.Client(intents=intents)

    @client.event
    async def on_ready():
        logger.info(f"Discord 로그인 완료: {client.user}")

        total_inserted = 0
        for guild in client.guilds:
            inserted = await backfill_guild(guild, pool, days)
            total_inserted += inserted

        logger.info(f"=== 백필 완료: 총 {total_inserted}개 새 레코드 ===")

        await pool.close()
        await client.close()

    await client.start(token)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="과거 채팅 메시지를 chat_activity 테이블에 백필")
    parser.add_argument("--days", type=int, default=30, help="며칠 전까지 조회할지 (기본값: 30)")
    args = parser.parse_args()

    asyncio.run(main(args.days))
