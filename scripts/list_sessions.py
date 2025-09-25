import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv


async def main(user_id: int, guild_id: int, limit: int = 5) -> None:
	repo_root = Path(__file__).resolve().parents[1]
	if str(repo_root) not in sys.path:
		sys.path.insert(0, str(repo_root))

	load_dotenv(encoding="utf-8-sig")
	from core.database import get_pool, close_pool

	pool = await get_pool()
	async with pool.acquire() as conn:
		records = await conn.fetch(
			"""
			SELECT session_id, started_at, ended_at, duration_seconds
			FROM voice_sessions
			WHERE user_id = $1 AND guild_id = $2
			ORDER BY session_id DESC
			LIMIT $3;
			""",
			user_id,
			guild_id,
			limit,
		)
		for r in records:
			print(dict(r))

	await close_pool()


if __name__ == "__main__":
	asyncio.run(main(364764044948799491, 1325465671727054899, 5))


