"""
과거 채팅 메시지를 조회하여 chat_activity 및 reaction_usage 테이블에 백필하는 스크립트.

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


async def record_reaction_usage_batch(pool: asyncpg.Pool, records: list[tuple[int, int, datetime, str]]) -> int:
    """Batch insert reaction usage records. Returns number of reaction records processed."""
    if not records:
        return 0

    async with pool.acquire() as conn:
        count = 0
        for user_id, guild_id, dt, emoji in records:
            usage_date = dt.date()
            await conn.execute(
                """
                INSERT INTO reaction_usage (user_id, guild_id, emoji, usage_date, count)
                VALUES ($1, $2, $3, $4, 1)
                ON CONFLICT (user_id, guild_id, emoji, usage_date)
                DO UPDATE SET count = reaction_usage.count + 1
                """,
                user_id,
                guild_id,
                emoji,
                usage_date,
            )
            count += 1
        return count


async def backfill_channel(
    channel: discord.TextChannel,
    pool: asyncpg.Pool,
    after_date: datetime,
    guild_id: int,
    valid_user_ids: set[int],
) -> tuple[int, int]:
    """Backfill chat activity and reaction usage from a single channel. Returns (chat_records, reaction_records)."""
    total_chat_inserted = 0
    total_reaction_count = 0
    chat_batch: list[tuple[int, int, datetime]] = []
    reaction_batch: list[tuple[int, int, datetime, str]] = []
    batch_size = 100
    message_count = 0

    try:
        async for message in channel.history(limit=None, after=after_date, oldest_first=True):
            if message.author.bot:
                continue

            # Skip users not in the database
            if message.author.id not in valid_user_ids:
                continue

            # Convert to KST
            created_kst = message.created_at.astimezone(KST).replace(tzinfo=None)
            chat_batch.append((message.author.id, guild_id, created_kst))

            # Collect reactions from this message
            for reaction in message.reactions:
                emoji_str = str(reaction.emoji)
                try:
                    async for user in reaction.users():
                        if user.bot:
                            continue
                        if user.id not in valid_user_ids:
                            continue
                        reaction_batch.append((user.id, guild_id, created_kst, emoji_str))
                except discord.Forbidden:
                    pass
                except Exception as e:
                    logger.warning(f"    반응 유저 조회 실패: {e}")

            message_count += 1

            if len(chat_batch) >= batch_size:
                inserted = await record_chat_activity_batch(pool, chat_batch)
                total_chat_inserted += inserted
                chat_batch.clear()

                reaction_count = await record_reaction_usage_batch(pool, reaction_batch)
                total_reaction_count += reaction_count
                reaction_batch.clear()

        # Process remaining batches
        if chat_batch:
            inserted = await record_chat_activity_batch(pool, chat_batch)
            total_chat_inserted += inserted
        if reaction_batch:
            reaction_count = await record_reaction_usage_batch(pool, reaction_batch)
            total_reaction_count += reaction_count

        logger.info(f"  #{channel.name}: {message_count} msgs, {total_chat_inserted} chat records, {total_reaction_count} reactions")

    except discord.Forbidden:
        logger.warning(f"  #{channel.name}: 접근 권한 없음 (스킵)")
    except Exception as e:
        logger.error(f"  #{channel.name}: 오류 발생 - {e}")

    return total_chat_inserted, total_reaction_count


async def get_valid_user_ids(pool: asyncpg.Pool, guild_id: int) -> set[int]:
    """Get set of user_ids that exist in the users table for this guild."""
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT user_id FROM users WHERE guild_id = $1",
            guild_id,
        )
        return {row["user_id"] for row in rows}


async def backfill_guild(
    guild: discord.Guild,
    pool: asyncpg.Pool,
    days: int,
) -> tuple[int, int]:
    """Backfill chat activity and reaction usage for all channels in a guild."""
    after_date = datetime.now(timezone.utc) - timedelta(days=days)
    total_chat = 0
    total_reaction = 0

    logger.info(f"길드 '{guild.name}' (ID: {guild.id}) 백필 시작...")
    logger.info(f"  조회 기간: {days}일 전부터 현재까지")

    # Get valid user IDs from database
    valid_user_ids = await get_valid_user_ids(pool, guild.id)
    logger.info(f"  DB에 등록된 유저 수: {len(valid_user_ids)}명")

    # Get all text channels
    text_channels = [ch for ch in guild.channels if isinstance(ch, discord.TextChannel)]
    logger.info(f"  텍스트 채널 수: {len(text_channels)}")

    for channel in text_channels:
        chat, reaction = await backfill_channel(channel, pool, after_date, guild.id, valid_user_ids)
        total_chat += chat
        total_reaction += reaction
        # Small delay to avoid rate limiting
        await asyncio.sleep(0.5)

    # Also check threads in forums
    for channel in guild.channels:
        if isinstance(channel, discord.ForumChannel):
            logger.info(f"  포럼 '{channel.name}' 스레드 조회 중...")
            try:
                threads = channel.threads
                for thread in threads:
                    chat, reaction = await backfill_channel(thread, pool, after_date, guild.id, valid_user_ids)
                    total_chat += chat
                    total_reaction += reaction
                    await asyncio.sleep(0.5)
            except Exception as e:
                logger.warning(f"  포럼 '{channel.name}' 스레드 조회 실패: {e}")

    logger.info(f"길드 '{guild.name}' 완료: 채팅 {total_chat}개, 반응 {total_reaction}개")
    return total_chat, total_reaction


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

        total_chat = 0
        total_reaction = 0
        for guild in client.guilds:
            chat, reaction = await backfill_guild(guild, pool, days)
            total_chat += chat
            total_reaction += reaction

        logger.info(f"=== 백필 완료: 채팅 {total_chat}개, 반응 {total_reaction}개 ===")

        await pool.close()
        await client.close()

    await client.start(token)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="과거 채팅 메시지를 chat_activity 테이블에 백필")
    parser.add_argument("--days", type=int, default=30, help="며칠 전까지 조회할지 (기본값: 30)")
    args = parser.parse_args()

    asyncio.run(main(args.days))
