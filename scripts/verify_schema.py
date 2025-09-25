import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv


async def main() -> None:
	repo_root = Path(__file__).resolve().parents[1]
	if str(repo_root) not in sys.path:
		sys.path.insert(0, str(repo_root))

	load_dotenv(encoding="utf-8-sig")
	from core.database import get_pool, close_pool

	pool = await get_pool()
	async with pool.acquire() as conn:
		# Check tables existence in current schema
		tables = [
			"users",
			"voice_sessions",
			"daily_streaks",
		]
		for tbl in tables:
			exists = await conn.fetchval(
				"""
				SELECT EXISTS (
					SELECT 1
					FROM information_schema.tables
					WHERE table_schema = 'public' AND table_name = $1
				);
				""",
				tbl,
			)
			print(f"table:{tbl} exists={bool(exists)}")

		# Verify an index as sample
		idx_exists = await conn.fetchval(
			"""
			SELECT EXISTS (
				SELECT 1 FROM pg_indexes WHERE schemaname='public' AND indexname='idx_sessions_user_guild'
			);
			"""
		)
		print(f"index:idx_sessions_user_guild exists={bool(idx_exists)}")

	await close_pool()


if __name__ == "__main__":
	asyncio.run(main())


