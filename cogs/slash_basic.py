import logging

import discord
from discord import app_commands
from discord.ext import commands

from core.leveling import calculate_level, xp_to_next_level


class BasicSlash(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="ping", description="봇 지연 시간 확인")
    async def ping(self, interaction: discord.Interaction) -> None:
        latency_ms = round(self.bot.latency * 1000)
        await interaction.response.send_message(f"pong: {latency_ms}ms", ephemeral=True)

    @app_commands.command(name="help", description="기본 도움말")
    async def help(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_message(
            "기본 명령어: /ping — 지연 시간 확인", ephemeral=True
        )

    @app_commands.command(name="level", description="현재 레벨과 다음 레벨까지 남은 XP")
    async def level(self, interaction: discord.Interaction) -> None:
        # Placeholder: total_xp는 users.xp에 저장될 예정이지만, 아직 xp 저장은 다음 단계에서 연결됨
        await interaction.response.send_message(
            "레벨 시스템이 활성화되었습니다. 곧 진행 상황이 표시됩니다.", ephemeral=True
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(BasicSlash(bot))


