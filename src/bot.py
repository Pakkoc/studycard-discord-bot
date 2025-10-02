import asyncio
import logging
import os
import sys
from pathlib import Path

import discord
from discord.ext import commands
from datetime import datetime, timezone
from typing import Optional
from dotenv import load_dotenv


def get_env_int(name: str, default: int) -> int:
    """Read integer from environment variables with a safe fallback."""
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except Exception:
        return default


def load_environment_variables() -> None:
    load_dotenv()


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )


async def run_startup_checks() -> None:
    required_vars = [
        "DISCORD_BOT_TOKEN",
    ]
    missing = [name for name in required_vars if not os.getenv(name)]
    if missing:
        logging.warning("Missing environment variables: %s", ", ".join(missing))


def pick_levelup_channel(guild: discord.Guild) -> Optional[discord.TextChannel]:
    """Choose channel to send level-up messages.

    Priority:
    1) .env LEVELUP_CHANNEL_ID
    2) guild.system_channel
    3) first text channel bot can send to
    """
    # 1) Global override via env
    chan_id = os.getenv("LEVELUP_CHANNEL_ID")
    if chan_id and chan_id.isdigit():
        ch = guild.get_channel(int(chan_id))
        if ch and isinstance(ch, discord.TextChannel) and ch.permissions_for(guild.me).send_messages:
            return ch

    # 2) system channel
    if guild.system_channel and guild.system_channel.permissions_for(guild.me).send_messages:
        return guild.system_channel

    # 3) any sendable text channel
    for ch in guild.text_channels:
        if ch.permissions_for(guild.me).send_messages:
            return ch
    return None


async def main() -> None:
    load_environment_variables()
    configure_logging()
    await run_startup_checks()

    # Global message auto-delete delay in seconds (0 disables)
    message_delete_after_sec = get_env_int("BOT_MESSAGE_DELETE_AFTER_SEC", 0)

    intents = discord.Intents.default()
    intents.members = True  # needed for member enumerate and join/remove events
    intents.message_content = False
    intents.voice_states = True

    bot = commands.Bot(command_prefix="!", intents=intents)

    @bot.event
    async def on_ready():
        logging.info("Logged in as %s (ID: %s)", bot.user, bot.user.id)
        try:
            # Finalize any open sessions from previous run
            try:
                from core.database import finalize_open_sessions

                min_session_sec = get_env_int("VOICE_MIN_SESSION_SEC", 180)
                finalized = await finalize_open_sessions(min_duration_seconds=min_session_sec)
                if finalized:
                    logging.info("Finalized %s open sessions from previous run", finalized)
            except Exception as finalize_exc:
                logging.warning("Finalize open sessions failed: %s", finalize_exc)

            dev_guild_id = os.getenv("DEV_GUILD_ID")
            if dev_guild_id and dev_guild_id.isdigit():
                guild = discord.Object(id=int(dev_guild_id))
                bot.tree.copy_global_to(guild=guild)
                await bot.tree.sync(guild=guild)
                logging.info("Slash commands synced to guild %s", dev_guild_id)
            else:
                # Immediate per-guild sync for all guilds the bot is currently in
                if bot.guilds:
                    for g in bot.guilds:
                        try:
                            bot.tree.copy_global_to(guild=g)
                            await bot.tree.sync(guild=g)
                            logging.info("Slash commands synced to guild %s", g.id)
                        except Exception as sync_exc:
                            logging.warning("Guild sync failed for %s: %s", g.id, sync_exc)
                # Also request global sync for eventual propagation
                await bot.tree.sync()
                logging.info("Global slash commands sync requested")

            # Pre-provision user records for all current guild members so /profile works immediately
            try:
                from core.database import ensure_users_for_guild, set_user_nicknames, set_user_student_nos
                for g in bot.guilds:
                    member_ids = [m.id for m in g.members if not m.bot]
                    # Upsert all users
                    if not member_ids:
                        member_ids = []
                        try:
                            async for m in g.fetch_members(limit=None):
                                if not m.bot:
                                    member_ids.append(m.id)
                        except Exception as fetch_exc:
                            logging.warning("Member fetch failed for guild %s: %s", g.id, fetch_exc)
                    await ensure_users_for_guild(g.id, member_ids)
                    logging.info("Ensured %s user records for guild %s", len(member_ids), g.id)

                    # Upsert nicknames for all existing members
                    try:
                        user_id_to_nick = {}
                        user_id_to_stuno = {}
                        for m in g.members:
                            if m.bot:
                                continue
                            user_id_to_nick[m.id] = m.nick or m.display_name or str(m)
                            # compute student number base (YYMMDD + order)
                            if m.joined_at:
                                base = m.joined_at.astimezone(timezone.utc).strftime("%y%m%d")
                                same_day = [mm for mm in g.members if mm.joined_at and mm.joined_at.date() == m.joined_at.date() and not mm.bot]
                                same_day_sorted = sorted(same_day, key=lambda mm: (mm.joined_at, mm.id))
                                try:
                                    idx = next(i for i, mm in enumerate(same_day_sorted) if mm.id == m.id)
                                except StopIteration:
                                    idx = 0
                                suffix = f"{idx + 1:02d}"
                                user_id_to_stuno[m.id] = f"{base}{suffix}"
                        if not user_id_to_nick:
                            # attempt fetch if cache empty
                            async for m in g.fetch_members(limit=None):
                                if not m.bot:
                                    user_id_to_nick[m.id] = m.nick or m.display_name or str(m)
                                    if m.joined_at:
                                        base = m.joined_at.astimezone(timezone.utc).strftime("%y%m%d")
                                        same_day = [mm for mm in g.members if mm.joined_at and mm.joined_at.date() == m.joined_at.date() and not mm.bot]
                                        same_day_sorted = sorted(same_day, key=lambda mm: (mm.joined_at, mm.id))
                                        try:
                                            idx = next(i for i, mm in enumerate(same_day_sorted) if mm.id == m.id)
                                        except StopIteration:
                                            idx = 0
                                        suffix = f"{idx + 1:02d}"
                                        user_id_to_stuno[m.id] = f"{base}{suffix}"
                        await set_user_nicknames(g.id, user_id_to_nick)
                        await set_user_student_nos(g.id, user_id_to_stuno)
                        logging.info("Upserted nicknames for %s users in guild %s", len(user_id_to_nick), g.id)
                    except Exception as nick_exc:
                        logging.warning("Nickname upsert failed for guild %s: %s", g.id, nick_exc)
            except Exception as prov_exc:
                logging.warning("Member pre-provision failed: %s", prov_exc)
        except Exception as exc:
            logging.warning("Failed to sync commands: %s", exc)

    # In-memory map: (guild_id, user_id) -> session start datetime
    active_sessions: dict[tuple[int, int], datetime] = {}

    @bot.event
    async def on_member_join(member: discord.Member):
        try:
            from core.database import ensure_user, set_user_nickname, set_user_student_no
            await ensure_user(member.id, member.guild.id)
            # Mark status active on join
            try:
                from core.database import get_pool
                pool = await get_pool()
                async with pool.acquire() as conn:
                    await conn.execute(
                        "UPDATE users SET status='active' WHERE user_id=$1 AND guild_id=$2",
                        member.id,
                        member.guild.id,
                    )
            except Exception:
                pass
            # Store current nickname/display name into DB
            nickname = member.nick or member.display_name or str(member)
            await set_user_nickname(member.id, member.guild.id, nickname)
            # Store student number
            if member.joined_at:
                base = member.joined_at.astimezone(timezone.utc).strftime("%y%m%d")
                same_day = [m for m in member.guild.members if m.joined_at and m.joined_at.date() == member.joined_at.date() and not m.bot]
                same_day_sorted = sorted(same_day, key=lambda m: (m.joined_at, m.id))
                try:
                    idx = next(i for i, m in enumerate(same_day_sorted) if m.id == member.id)
                except StopIteration:
                    idx = 0
                suffix = f"{idx + 1:02d}"
                await set_user_student_no(member.id, member.guild.id, f"{base}{suffix}")
            logging.info("Ensured user record for joined member %s in guild %s", member.id, member.guild.id)
        except Exception as exc:
            logging.warning("Failed to ensure user on join: %s", exc)

    @bot.event
    async def on_member_remove(member: discord.Member):
        try:
            # Control whether to reset stats on leave via env (default: 0 => keep data)
            reset_on_leave = get_env_int("RESET_USER_STATS_ON_LEAVE", 0)
            if reset_on_leave <= 0:
                logging.info(
                    "Member %s left guild %s; keeping stats as configured (RESET_USER_STATS_ON_LEAVE=0)",
                    member.id,
                    member.guild.id,
                )
                # Mark status left
                try:
                    from core.database import get_pool
                    pool = await get_pool()
                    async with pool.acquire() as conn:
                        await conn.execute(
                            "UPDATE users SET status='left' WHERE user_id=$1 AND guild_id=$2",
                            member.id,
                            member.guild.id,
                        )
                except Exception:
                    pass
                return
            from core.database import purge_user_non_session_data
            await purge_user_non_session_data(member.id, member.guild.id)
            logging.info(
                "Purged non-session data for leaving member %s in guild %s (RESET_USER_STATS_ON_LEAVE=1)",
                member.id,
                member.guild.id,
            )
            # Also mark status left
            try:
                from core.database import get_pool
                pool = await get_pool()
                async with pool.acquire() as conn:
                    await conn.execute(
                        "UPDATE users SET status='left' WHERE user_id=$1 AND guild_id=$2",
                        member.id,
                        member.guild.id,
                    )
            except Exception:
                pass
        except Exception as exc:
            logging.warning("Failed to handle member remove: %s", exc)

    @bot.event
    async def on_member_update(before: discord.Member, after: discord.Member):
        """Update DB immediately when a member's server nickname changes."""
        try:
            # Only proceed if nickname changed
            if before.nick == after.nick:
                return
            from core.database import ensure_user, set_user_nickname
            await ensure_user(after.id, after.guild.id)
            nickname = after.nick or after.display_name or str(after)
            await set_user_nickname(after.id, after.guild.id, nickname)
            logging.info(
                "Updated nickname for member %s in guild %s to '%s'", after.id, after.guild.id, nickname
            )
        except Exception as exc:
            logging.warning("Failed to handle nickname update: %s", exc)

    # Award XP for posts in specific channels with a simple per-user cooldown
    # Read comma-separated channel IDs from .env POST_XP_CHANNEL_IDS
    channels_env = os.getenv("POST_XP_CHANNEL_IDS", "").replace(" ", "").strip()
    POST_XP_CHANNEL_IDS: set[int] = set(int(tok) for tok in channels_env.split(",") if tok.isdigit())
    POST_XP_AMOUNT = get_env_int("POST_XP_AMOUNT", 3)
    POST_XP_COOLDOWN_SEC = get_env_int("POST_XP_COOLDOWN_SEC", 60)
    _last_post_ts: dict[tuple[int, int], float] = {}

    @bot.event
    async def on_message(message: discord.Message):
        # Ignore bot/self
        if message.author.bot:
            return
        # Only handle plain text channels here. Threads (forum posts & replies) are handled separately.
        if not isinstance(message.channel, discord.TextChannel):
            return
        channel_id = message.channel.id
        if channel_id not in POST_XP_CHANNEL_IDS:
            return

        # per-user cooldown
        from time import time
        key = (message.guild.id if message.guild else 0, message.author.id)
        now_ts = time()
        last = _last_post_ts.get(key, 0)
        if now_ts - last < POST_XP_COOLDOWN_SEC:
            return
        _last_post_ts[key] = now_ts

        try:
            from core.database import add_xp
            result = await add_xp(message.author.id, message.guild.id, POST_XP_AMOUNT)
            if result and result.get("new_level", 0) > result.get("old_level", 0):
                channel = pick_levelup_channel(message.guild)
                if channel:
                    try:
                        from core.leveling import get_level_title as _ltitle
                        lvl = int(result.get("new_level", 0))
                        title = _ltitle(lvl)
                    except Exception:
                        lvl = int(result.get("new_level", 0))
                        title = f"L{lvl}"
                    await channel.send(
                        f"🎉 <@{message.author.id}> 레벨업! 새 레벨: {title} (L{lvl}, 누적 XP: {result['total_xp']})",
                    )
                else:
                    logging.warning("No available channel to send level-up message in guild %s", message.guild.id)
        except Exception as exc:
            logging.warning("Failed to add post XP: %s", exc)

    @bot.event
    async def on_thread_create(thread: discord.Thread):
        # Award XP when a new forum post (thread) is created in allowed forum channels.
        try:
            parent_id = thread.parent_id
            if parent_id not in POST_XP_CHANNEL_IDS:
                return
            guild = thread.guild
            if guild is None:
                return
            author_id: Optional[int] = getattr(thread, "owner_id", None)
            if author_id is None:
                # Fallback: fetch first message author
                first_msg_author_id: Optional[int] = None
                try:
                    async for msg in thread.history(limit=1, oldest_first=True):
                        first_msg_author_id = msg.author.id if msg.author and not msg.author.bot else None
                        break
                except Exception:
                    first_msg_author_id = None
                author_id = first_msg_author_id
            if author_id is None:
                return

            from core.database import add_xp
            await add_xp(author_id, guild.id, POST_XP_AMOUNT)
        except Exception as exc:
            logging.warning("Failed to add XP for thread create: %s", exc)


    @bot.event
    async def on_voice_state_update(member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        try:
            from core.database import record_voice_session
        except Exception:
            record_voice_session = None  # type: ignore

        guild_id = member.guild.id if member.guild else None
        if guild_id is None:
            return

        key = (guild_id, member.id)
        before_channel = before.channel.id if before and before.channel else None
        after_channel = after.channel.id if after and after.channel else None

        # Joined a voice channel
        if before_channel is None and after_channel is not None:
            # ensure user exists on first activity as well (safety)
            try:
                from core.database import ensure_user, set_user_nickname
                await ensure_user(member.id, guild_id)
                nickname = member.nick or member.display_name or str(member)
                await set_user_nickname(member.id, guild_id, nickname)
            except Exception:
                pass
            active_sessions[key] = datetime.now(timezone.utc)
            logging.info("Voice session started: user=%s guild=%s", member.id, guild_id)
            return

        # Moved between voice channels (voice -> voice)
        if (
            before_channel is not None
            and after_channel is not None
            and before_channel != after_channel
        ):
            now = datetime.now(timezone.utc)
            started_at = active_sessions.pop(key, None)
            if started_at and record_voice_session:
                try:
                    duration = int((now - started_at).total_seconds())
                    await record_voice_session(member.id, guild_id, started_at, now, duration)
                    logging.info(
                        "Voice session moved: user=%s guild=%s duration=%ss (from %s to %s)",
                        member.id,
                        guild_id,
                        duration,
                        before_channel,
                        after_channel,
                    )
                except Exception as exc:
                    logging.warning("Failed to record voice move session: %s", exc)

            # Start new session at the new channel immediately
            active_sessions[key] = now
            logging.info("Voice session restarted at new channel: user=%s guild=%s", member.id, guild_id)
            return

        # Left a voice channel completely
        if before_channel is not None and after_channel is None:
            started_at = active_sessions.pop(key, None)
            if not started_at:
                return
            ended_at = datetime.now(timezone.utc)
            duration = int((ended_at - started_at).total_seconds())
            logging.info(
                "Voice session ended: user=%s guild=%s duration=%ss", member.id, guild_id, duration
            )
            # Persist to DB for sessions meeting the minimum duration threshold
            min_session_sec = get_env_int("VOICE_MIN_SESSION_SEC", 180)
            if duration >= min_session_sec and record_voice_session:
                try:
                    result = await record_voice_session(
                        member.id, guild_id, started_at, ended_at, duration
                    )
                    if result and result.get("new_level", 0) > result.get("old_level", 0):
                        # Level-up! Send an ephemeral congrats to the user in a text channel if possible
                        try:
                            channel = pick_levelup_channel(member.guild)
                            if channel:
                                try:
                                    from core.leveling import get_level_title as _ltitle2
                                    lvl = int(result.get("new_level", 0))
                                    title = _ltitle2(lvl)
                                except Exception:
                                    lvl = int(result.get("new_level", 0))
                                    title = f"L{lvl}"
                                await channel.send(
                                    f"🎉 <@{member.id}> 레벨업! 새 레벨: {title} (L{lvl}, 누적 XP: {result['total_xp']})",
                                )
                            else:
                                logging.warning("No available channel to send level-up message in guild %s", member.guild.id)
                        except Exception as send_exc:
                            logging.warning("Failed to send level-up message: %s", send_exc)
                except Exception as exc:
                    logging.warning("Failed to record voice session: %s", exc)
            return

    token = os.getenv("DISCORD_BOT_TOKEN", "")
    if not token:
        logging.info("No DISCORD_BOT_TOKEN provided. Starting dummy loop then exit.")
        # Short no-op to validate event loop run
        await asyncio.sleep(0.1)
        return

    # Ensure repo root is importable so that 'cogs' (at project root) can be found
    repo_root = Path(__file__).resolve().parents[1]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    # Load only the profile slash command
    try:
        await bot.load_extension("cogs.profile_cog")
        logging.info("Loaded extension cogs.profile_cog")
    except Exception as exc:
        logging.warning("Failed to load extension cogs.profile_cog: %s", exc)

    await bot.start(token)


if __name__ == "__main__":
    asyncio.run(main())


