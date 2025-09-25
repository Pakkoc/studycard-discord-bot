from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands
from io import BytesIO
from datetime import datetime, timezone

from core.database import fetch_user_stats, fetch_recent_streak_days, fetch_month_streak_days
from core.leveling import calculate_level, compute_level_progress
from core.imaging import (
    render_profile_card,
    render_streak_calendar,
    compose_vertical_images,
    render_stats_and_month_calendar,
)


HOUSE_PATTERNS: list[tuple[str, str]] = [
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


class ProfileCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="profile", description="프로필 카드 보기")
    async def profile(self, interaction: discord.Interaction, member: discord.Member | None = None):
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
        )
        top_img = Image.open(profile_buf)
        bottom_img = Image.open(stats_buf)
        combined = compose_vertical_images(top_img, bottom_img)

        file = discord.File(combined, filename="profile.png")
        await interaction.response.send_message(file=file)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ProfileCog(bot))


