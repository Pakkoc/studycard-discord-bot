import os
from pathlib import Path
from dotenv import load_dotenv


def safe_load_dotenv() -> None:
    dotenv_path = Path(".env")
    if not dotenv_path.exists():
        return
    try:
        load_dotenv(dotenv_path=dotenv_path, encoding="utf-8")
        return
    except UnicodeDecodeError:
        try:
            # Fallback: try utf-16 and rewrite as utf-8 without BOM
            content = dotenv_path.read_text(encoding="utf-16")
            dotenv_path.write_text(content, encoding="utf-8")
            load_dotenv(dotenv_path=dotenv_path, encoding="utf-8")
        except Exception:
            # Last resort: ignore invalid bytes
            content = dotenv_path.read_bytes().decode("utf-8", errors="ignore")
            dotenv_path.write_text(content, encoding="utf-8")
            load_dotenv(dotenv_path=dotenv_path, encoding="utf-8")


def main() -> None:
    safe_load_dotenv()
    keys = ["DISCORD_BOT_TOKEN", "DATABASE_URL", "APP_ENV"]
    for key in keys:
        value = os.getenv(key)
        if value is None:
            print(f"{key}=<NOT SET>")
        elif key == "DISCORD_BOT_TOKEN" and value:
            print(f"{key}=<SET, LENGTH={len(value)}>\n(미리보기 보호를 위해 값은 표시하지 않습니다)")
        else:
            print(f"{key}={value}")


if __name__ == "__main__":
    main()


