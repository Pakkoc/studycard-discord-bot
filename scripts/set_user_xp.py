import asyncio
import argparse
import sys
from pathlib import Path
from dotenv import load_dotenv


async def main(user_id: int, guild_id: int, xp_value: int) -> None:
	repo_root = Path(__file__).resolve().parents[1]
	if str(repo_root) not in sys.path:
		sys.path.insert(0, str(repo_root))

	load_dotenv(encoding="utf-8-sig")
	from core.database import get_pool, close_pool, ensure_user_exists

	pool = await get_pool()
	async with pool.acquire() as conn:
		await ensure_user_exists(conn, user_id, guild_id)
		await conn.execute(
			"UPDATE users SET xp=$1 WHERE user_id=$2 AND guild_id=$3",
			xp_value,
			user_id,
			guild_id,
		)
		row = await conn.fetchrow(
			"SELECT xp, total_seconds FROM users WHERE user_id=$1 AND guild_id=$2",
			user_id,
			guild_id,
		)
		print(dict(row) if row else "<NO USER>")

	await close_pool()


if __name__ == "__main__":
	parser = argparse.ArgumentParser()
	parser.add_argument("--user", type=int, required=True)
	parser.add_argument("--guild", type=int, required=True)
	parser.add_argument("--xp", type=int, required=True)
	args = parser.parse_args()
	asyncio.run(main(args.user, args.guild, args.xp))


