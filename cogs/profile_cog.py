from __future__ import annotations

import discord
# from discord import app_commands
from discord.ext import commands
from io import BytesIO
from datetime import datetime, timezone
import os

from core.database import fetch_user_stats, fetch_month_streak_days
from core.leveling import compute_level_progress
from core.imaging import (
    render_profile_card,
    compose_vertical_images,
    render_stats_and_month_calendar,
)


def _load_house_patterns_from_env() -> list[tuple[str, str]]:
    """Parse HOUSE_PATTERNS env var like '키:라벨,키:라벨'.

    - 각 항목은 콤마(,)로 구분
    - 항목 내부는 콜론(:)으로 '키:라벨' 구성
    - 공백은 자동으로 트림
    - 잘못된 항목은 무시
    """
    raw = os.getenv("HOUSE_PATTERNS", "").strip()
    patterns: list[tuple[str, str]] = []
    if not raw:
        return patterns
    for item in raw.split(","):
        part = item.strip()
        if not part:
            continue
        if ":" not in part:
            continue
        k, v = part.split(":", 1)
        k = k.strip()
        v = v.strip()
        if k and v:
            patterns.append((k, v))
    return patterns


HOUSE_PATTERNS: list[tuple[str, str]] = _load_house_patterns_from_env() or [
    ("소용돌이", "소용돌이"),
    ("펭도리야", "펭도리야"),
    ("노블레빗", "노블레빗"),
    ("볼리베어", "볼리베어"),
]


def pick_house_name(member: discord.Member) -> str | None:
    for role in member.roles:
        rn = role.name or ""
        for key, label in HOUSE_PATTERNS:
            if key in rn:
                return label
    return None


def compute_grade_by_join_date(joined_at: datetime | None, now: datetime | None = None) -> int:
    if joined_at is None:
        return 1
    now = now or datetime.now(timezone.utc)
    days = (now.date() - joined_at.date()).days
    if days < 0:
        return 1
    return (days // 365) + 1


def is_house_leader(user: discord.abc.User | discord.Member) -> bool:
    """Return True if the invoker may view others' profiles.

    Priority:
    1) HOUSE_LEADER_ROLE_IDS (comma-separated role IDs)
    2) HOUSE_LEADER_ROLE_NAMES (comma-separated role names; exact match)
    3) Default role name exact match: '기숙사장'
    """
    if not isinstance(user, discord.Member):
        return False

    # 1) Role IDs (highest priority)
    raw_ids = os.getenv("HOUSE_LEADER_ROLE_IDS", "").strip()
    if raw_ids:
        role_ids: set[int] = set()
        for tok in raw_ids.split(","):
            tok = tok.strip()
            if not tok:
                continue
            try:
                role_ids.add(int(tok))
            except Exception:
                continue
        if role_ids and any(r.id in role_ids for r in user.roles):
            return True

    # 2) Role names (exact match)
    raw_names = os.getenv("HOUSE_LEADER_ROLE_NAMES", "").strip()
    if raw_names:
        names = {t.strip() for t in raw_names.split(",") if t.strip()}
        if names and any((r.name or "") in names for r in user.roles):
            return True

    # 3) Default fallback
    return any((r.name or "") == "기숙사장" for r in user.roles)


class ProfileCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # [removed] slash command /profile
    # @app_commands.guild_only()
    async def _deprecated_profile(self, interaction: discord.Interaction, member: discord.Member | None = None):
        # Only house leaders may view other users' profiles
        if member is not None and member.id != interaction.user.id:
            if not is_house_leader(interaction.user):
                await interaction.response.send_message("타인의 프로필은 기숙사장만 조회할 수 있습니다.", ephemeral=True)
                return
        target = member or interaction.user
        # Prefer server nickname if present
        # 서버 닉네임(멤버 별명) 우선 사용
        display_name = target.nick or target.display_name or str(target)
        stats = await fetch_user_stats(target.id, interaction.guild.id)
        if not stats:
            await interaction.response.send_message("데이터가 없습니다. 잠시 후 다시 시도하세요.", ephemeral=True)
            return

        level, xp_in_level, level_need, xp_to_next, progress = compute_level_progress(stats["xp"])

        # Try fetching avatar image
        avatar_bytes = await target.display_avatar.read() if target.display_avatar else None
        avatar_img = None
        if avatar_bytes:
            from PIL import Image
            from io import BytesIO as _BytesIO
            avatar_img = Image.open(_BytesIO(avatar_bytes))

        # Prepare subtitles: house + grade, and student number (join date)
        house_name = pick_house_name(target)
        if house_name is None:
            await interaction.response.send_message("기숙사를 먼저 선택해주세요.", ephemeral=True)
            return
        grade = compute_grade_by_join_date(getattr(target, "joined_at", None))
        subtitle_line1 = f"{house_name} {grade}학년" if house_name else f"{grade}학년"
        # Prefer DB stored student_no, fallback to computed
        from core.database import set_user_student_no
        joined = getattr(target, "joined_at", None)
        student_no = stats.get("student_no") or ""
        if not student_no and joined:
            base = joined.astimezone(timezone.utc).strftime("%y%m%d")
            same_day = [m for m in interaction.guild.members if m.joined_at and m.joined_at.date() == joined.date() and not m.bot]
            same_day_sorted = sorted(same_day, key=lambda m: (m.joined_at, m.id))
            try:
                idx = next(i for i, m in enumerate(same_day_sorted) if m.id == target.id)
            except StopIteration:
                idx = 0
            suffix = f"{idx + 1:02d}"
            student_no = f"{base}{suffix}"
            # Save back to DB for future reads
            try:
                await set_user_student_no(target.id, interaction.guild.id, student_no)
            except Exception:
                pass
        subtitle_line2 = f"학번 {student_no}" if student_no else None

        profile_buf: BytesIO = render_profile_card(
            username=display_name,
            level=level,
            xp=stats["xp"],
            today_seconds=stats["today_seconds"],
            week_seconds=stats["week_seconds"],
            month_seconds=stats["month_seconds"],
            total_seconds=stats["total_seconds"],
            progress_ratio=progress,
            xp_in_level=xp_in_level,
            level_need=level_need,
            avatar_image=avatar_img,
            title_text=display_name,
            subtitle_line1=subtitle_line1,
            subtitle_line2=subtitle_line2,
            house_name=house_name,
        )
        # Fetch month streak for stats+calendar section
        month = await fetch_month_streak_days(target.id, interaction.guild.id)
        from PIL import Image
        stats_buf: BytesIO = render_stats_and_month_calendar(
            display_name,
            stats["today_seconds"],
            stats["week_seconds"],
            stats["month_seconds"],
            stats["total_seconds"],
            int(month["year"]),
            int(month["month"]),
            set(int(d) for d in month["days"]),
            int(month["today"]) if month["today"] else None,
            house_name=house_name,
        )
        top_img = Image.open(profile_buf)
        bottom_img = Image.open(stats_buf)
        combined = compose_vertical_images(top_img, bottom_img, spacing=-24)

        file = discord.File(combined, filename="profile.png")
        # Auto-delete after configured seconds (0 disables)
        try:
            delete_after_raw = os.getenv("BOT_MESSAGE_DELETE_AFTER_SEC", "0").strip()
            delete_after = int(delete_after_raw) if delete_after_raw.isdigit() else 0
        except Exception:
            delete_after = 0
        await interaction.response.send_message(file=file, delete_after=delete_after if delete_after > 0 else None)


    @commands.command(name="학생증")
    @commands.guild_only()
    async def student_card(self, ctx: commands.Context, member: discord.Member | None = None):
        # Only house leaders may view others' profiles
        if member is not None and member.id != ctx.author.id:
            if not is_house_leader(ctx.author):
                await ctx.reply("타인의 프로필은 기숙사장만 조회할 수 있습니다.")
                return
        target = member or ctx.author
        # Prefer server nickname if present
        display_name = target.nick or target.display_name or str(target)
        stats = await fetch_user_stats(target.id, ctx.guild.id)
        if not stats:
            await ctx.reply("데이터가 없습니다. 잠시 후 다시 시도하세요.")
            return

        level, xp_in_level, level_need, xp_to_next, progress = compute_level_progress(stats["xp"])

        # Try fetching avatar image
        avatar_bytes = await target.display_avatar.read() if target.display_avatar else None
        avatar_img = None
        if avatar_bytes:
            from PIL import Image
            from io import BytesIO as _BytesIO
            avatar_img = Image.open(_BytesIO(avatar_bytes))

        # Prepare subtitles: house + grade, and student number (join date)
        house_name = pick_house_name(target)
        if house_name is None:
            await ctx.reply("기숙사를 먼저 선택해주세요.")
            return
        grade = compute_grade_by_join_date(getattr(target, "joined_at", None))
        subtitle_line1 = f"{house_name} {grade}학년" if house_name else f"{grade}학년"
        # Prefer DB stored student_no, fallback to computed
        from core.database import set_user_student_no
        joined = getattr(target, "joined_at", None)
        student_no = stats.get("student_no") or ""
        if not student_no and joined:
            base = joined.astimezone(timezone.utc).strftime("%y%m%d")
            same_day = [m for m in ctx.guild.members if m.joined_at and m.joined_at.date() == joined.date() and not m.bot]
            same_day_sorted = sorted(same_day, key=lambda m: (m.joined_at, m.id))
            try:
                idx = next(i for i, m in enumerate(same_day_sorted) if m.id == target.id)
            except StopIteration:
                idx = 0
            suffix = f"{idx + 1:02d}"
            student_no = f"{base}{suffix}"
            # Save back to DB for future reads
            try:
                await set_user_student_no(target.id, ctx.guild.id, student_no)
            except Exception:
                pass
        subtitle_line2 = f"학번 {student_no}" if student_no else None

        profile_buf: BytesIO = render_profile_card(
            username=display_name,
            level=level,
            xp=stats["xp"],
            today_seconds=stats["today_seconds"],
            week_seconds=stats["week_seconds"],
            month_seconds=stats["month_seconds"],
            total_seconds=stats["total_seconds"],
            progress_ratio=progress,
            xp_in_level=xp_in_level,
            level_need=level_need,
            avatar_image=avatar_img,
            title_text=display_name,
            subtitle_line1=subtitle_line1,
            subtitle_line2=subtitle_line2,
            house_name=house_name,
        )
        # Fetch month streak for stats+calendar section
        month = await fetch_month_streak_days(target.id, ctx.guild.id)
        from PIL import Image
        stats_buf: BytesIO = render_stats_and_month_calendar(
            display_name,
            stats["today_seconds"],
            stats["week_seconds"],
            stats["month_seconds"],
            stats["total_seconds"],
            int(month["year"]),
            int(month["month"]),
            set(int(d) for d in month["days"]),
            int(month["today"]) if month["today"] else None,
            house_name=house_name,
        )
        top_img = Image.open(profile_buf)
        bottom_img = Image.open(stats_buf)
        combined = compose_vertical_images(top_img, bottom_img, spacing=-5)

        file = discord.File(combined, filename="profile.png")
        # Auto-delete after configured seconds (0 disables)
        try:
            delete_after_raw = os.getenv("BOT_MESSAGE_DELETE_AFTER_SEC", "0").strip()
            delete_after = int(delete_after_raw) if delete_after_raw.isdigit() else 0
        except Exception:
            delete_after = 0
        await ctx.reply(file=file, delete_after=delete_after if delete_after > 0 else None)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ProfileCog(bot))


