import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv


async def main(user_id: int, guild_id: int) -> None:
	repo_root = Path(__file__).resolve().parents[1]
	if str(repo_root) not in sys.path:
		sys.path.insert(0, str(repo_root))

	load_dotenv(encoding="utf-8-sig")
	from core.database import fetch_user_stats, close_pool

	stats = await fetch_user_stats(user_id, guild_id)
	print(stats if stats is not None else "<NO USER>")
	await close_pool()


if __name__ == "__main__":
	asyncio.run(main(364764044948799491, 1325465671727054899))


