from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands
from io import BytesIO
from datetime import datetime, timezone, timedelta

# 한국 시간대 (KST, UTC+9)
KST = timezone(timedelta(hours=9))
import os

from core.database import fetch_user_stats, fetch_month_streak_days
from core.leveling import compute_level_progress
from core.imaging import (
    render_profile_card,
    compose_vertical_images,
    render_stats_and_month_calendar,
    render_annual_grass_image,
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


def _load_keywords_from_env(var_name: str, default: list[str]) -> list[str]:
    raw = os.getenv(var_name, "").strip()
    if not raw:
        return default
    kws: list[str] = []
    for item in raw.split(","):
        tok = item.strip()
        if tok:
            kws.append(tok)
    return kws


# 장학생 배지(voost 아이콘) 노출을 위한 역할명 키워드 (부분일치)
SCHOLAR_ROLE_KEYWORDS: list[str] = _load_keywords_from_env("SCHOLAR_ROLE_KEYWORDS", ["장학생"])  # 예: "장학생,슈퍼장학생"


def has_scholar_role(member: discord.Member) -> bool:
    try:
        for role in member.roles:
            rn = role.name or ""
            for key in SCHOLAR_ROLE_KEYWORDS:
                if key and key in rn:
                    return True
    except Exception:
        pass
    return False


def compute_grade_by_join_date(joined_at: datetime | None, now: datetime | None = None) -> int:
    if joined_at is None:
        return 1
    now = now or datetime.now(KST)
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
            base = joined.astimezone(KST).strftime("%y%m%d")
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
            voost_visible=has_scholar_role(target),
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
        await interaction.response.send_message(file=file, ephemeral=True)


    @app_commands.command(name="학생증", description="학생증 프로필을 생성합니다")
    @app_commands.guild_only()
    async def student_card(self, interaction: discord.Interaction, member: discord.Member | None = None):
        # Only house leaders may view others' profiles
        if member is not None and member.id != interaction.user.id:
            if not is_house_leader(interaction.user):
                await interaction.response.send_message("타인의 프로필은 기숙사장만 조회할 수 있습니다.", ephemeral=True)
                return
        target = member or interaction.user
        # Prefer server nickname if present
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
            base = joined.astimezone(KST).strftime("%y%m%d")
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
            voost_visible=has_scholar_role(target),
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
        combined = compose_vertical_images(top_img, bottom_img, spacing=-5)

        file = discord.File(combined, filename="profile.png")
        await interaction.response.send_message(file=file, ephemeral=True)

    @app_commands.command(name="잔디", description="연간 잔디(공부 달력)를 이미지로 보여줍니다")
    @app_commands.guild_only()
    async def yearly_grass(self, interaction: discord.Interaction, year: int | None = None, member: discord.Member | None = None):
        # 권한: 타인 조회는 기숙사장만
        if member is not None and member.id != interaction.user.id:
            if not is_house_leader(interaction.user):
                await interaction.response.send_message("타인의 잔디는 기숙사장만 조회할 수 있습니다.", ephemeral=True)
                return
        target = member or interaction.user
        if interaction.guild is None:
            await interaction.response.send_message("길드 컨텍스트에서만 사용할 수 있습니다.", ephemeral=True)
            return
        y = year or datetime.now(KST).year

        try:
            from core.database import (
                fetch_user_calendar_year_kst,
                fetch_guild_per_user_daily_max_hours_kst,
                ensure_user,
            )
            # Prepare small avatar for title icon
            from PIL import Image
            avatar_bytes = await target.display_avatar.read() if getattr(target, "display_avatar", None) else None
            avatar_img = Image.open(BytesIO(avatar_bytes)).convert("RGBA") if avatar_bytes else None
            await ensure_user(target.id, interaction.guild.id)
            # 데이터 조회
            data = await fetch_user_calendar_year_kst(target.id, interaction.guild.id, y)
            # cap: 12시간 고정 (12시간 이상이면 최대 색상)
            cap_hours = 12.0

            # 이미지 렌더
            house_name = pick_house_name(target)
            buf = render_annual_grass_image(
                username=target.nick or target.display_name or str(target),
                year=y,
                days=[(d["date"], int(d["seconds"])) for d in data],
                cap_hours=cap_hours,
                house_name=house_name,
                avatar_image=avatar_img,
            )
            file = discord.File(buf, filename=f"grass_{y}.png")
            await interaction.response.send_message(file=file, ephemeral=True)
        except Exception as exc:
            await interaction.response.send_message("잔디 이미지를 생성하지 못했습니다. 잠시 후 다시 시도하세요.", ephemeral=True)
            raise


async def setup(bot: commands.Bot) -> None:
    cog = ProfileCog(bot)
    # Adding the cog will auto-register app_commands defined on it; no manual tree.add_command to avoid duplicates
    await bot.add_cog(cog)


