import discord
from discord import app_commands
from discord.ext import commands
from io import BytesIO

from core.database import fetch_recent_streak_days
from core.imaging import render_streak_calendar


class StreakCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="streak", description="최근 35일 스트릭 캘린더 보기")
    async def streak(self, interaction: discord.Interaction, member: discord.Member | None = None):
        target = member or interaction.user
        data = await fetch_recent_streak_days(target.id, interaction.guild.id)
        played = data["played"]
        today_iso = data["today"]
        buf: BytesIO = render_streak_calendar(target.display_name or str(target), played, today_iso)
        file = discord.File(buf, filename="streak.png")
        await interaction.response.send_message(file=file)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(StreakCog(bot))


