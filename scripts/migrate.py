import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv


async def main() -> None:
	# Ensure repo root import path
	repo_root = Path(__file__).resolve().parents[1]
	if str(repo_root) not in sys.path:
		sys.path.insert(0, str(repo_root))

	load_dotenv(encoding="utf-8-sig")
	from core.database import execute_sql_file, close_pool

	migrations = [
		repo_root / "assets" / "db" / "migrations" / "migration_001_init.sql",
		repo_root / "assets" / "db" / "migrations" / "migration_002_drop_user_achievements.sql",
		repo_root / "assets" / "db" / "migrations" / "migration_003_drop_users_language.sql",
		repo_root / "assets" / "db" / "migrations" / "migration_004_add_users_nickname.sql",
		repo_root / "assets" / "db" / "migrations" / "migration_005_add_users_student_no.sql",
		repo_root / "assets" / "db" / "migrations" / "migration_006_enable_rls.sql",
		repo_root / "assets" / "db" / "migrations" / "migration_007_enable_rls_read_policies.sql",
		repo_root / "assets" / "db" / "migrations" / "migration_008_drop_channels.sql",
		repo_root / "assets" / "db" / "migrations" / "migration_009_add_users_status.sql",
		repo_root / "assets" / "db" / "migrations" / "migration_010_add_users_level.sql",
		repo_root / "assets" / "db" / "migrations" / "migration_011_add_users_level_name.sql",
	]
	for m in migrations:
		await execute_sql_file(str(m))
		print(f"Migration applied: {m.name}")
	await close_pool()


if __name__ == "__main__":
	asyncio.run(main())
