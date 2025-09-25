import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv


async def main() -> None:
	# Ensure repo root is in sys.path for `core` package import
	repo_root = Path(__file__).resolve().parents[1]
	if str(repo_root) not in sys.path:
		sys.path.insert(0, str(repo_root))

	# Use utf-8-sig to gracefully handle BOM from some editors on Windows
	load_dotenv(encoding="utf-8-sig")
	from core.database import test_connection, close_pool
	try:
		value = await test_connection()
		print(f"SELECT 1 result: {value}")
	except Exception as exc:
		print(f"Connection failed: {exc}")
	finally:
		await close_pool()


if __name__ == "__main__":
	asyncio.run(main())
