import asyncio
import sys
from pathlib import Path
from dotenv import load_dotenv


async def main() -> None:
	repo_root = Path(__file__).resolve().parents[1]
	if str(repo_root) not in sys.path:
		sys.path.insert(0, str(repo_root))

	load_dotenv(encoding="utf-8-sig")

	from core.database import get_pool, close_pool
	from core.leveling import calculate_level, get_level_title

	pool = await get_pool()
	updated = 0
	async with pool.acquire() as conn:
		rows = await conn.fetch("SELECT user_id, guild_id, COALESCE(xp,0) AS xp FROM users")
		for r in rows:
			uid = int(r["user_id"]) if r["user_id"] is not None else None
			gid = int(r["guild_id"]) if r["guild_id"] is not None else None
			xp = int(r["xp"]) if r["xp"] is not None else 0
			lvl = calculate_level(xp)
			name = get_level_title(lvl)
			await conn.execute(
				"UPDATE users SET level=$1, level_name=$2 WHERE user_id=$3 AND guild_id=$4",
				int(lvl),
				name,
				uid,
				gid,
			)
			updated += 1
	print(f"Backfilled level fields for {updated} users")
	await close_pool()


if __name__ == "__main__":
	asyncio.run(main())


