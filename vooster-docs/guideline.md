# Code Guideline: Discord Silent Study Tracker Bot

This document provides the official coding standards and architectural patterns for the Silent Study Tracker Bot project. Adherence to these guidelines is mandatory to ensure code quality, maintainability, and consistency.

## 1. Project Overview

The project is a monolithic Python application built with the `discord.py` library. It serves as a real-time tracker for user voice activity on Discord, providing gamification features like levels, achievements, and streaks.

### Key Architectural Decisions
- **Monolithic Application**: A single, asynchronous Python process handles all logic.
- **Direct Database Access**: We use the `asyncpg` library for direct, high-performance communication with a PostgreSQL database. ORMs (like SQLAlchemy) are explicitly excluded for simplicity and performance.
- **Stateless Service**: The application maintains no critical state in memory. The PostgreSQL database is the single source of truth, allowing for graceful restarts via `systemd`.
- **Componentization via Cogs**: `discord.py` Cogs are used to modularize command groups and event listeners.

## 2. Core Principles

- **Simplicity Over Complexity**: Prefer direct, readable code over premature or unnecessary abstractions.
- **Efficiency is Key**: Write non-blocking, asynchronous code and optimized database queries suitable for a resource-constrained environment.
- **The Database is Truth**: All persistent user and server state MUST reside in the database to ensure data integrity across restarts.
- **Clarity for Future Selves**: Code is read more often than it is written. Prioritize clarity, type hinting, and meaningful naming.

## 3. Language-Specific Guidelines (Python)

### File Organization and Directory Structure

All development MUST follow this standardized directory structure to ensure modularity and separation of concerns.

```
/
├── assets/                 # Static assets: fonts, image templates, etc.
├── cogs/                   # Discord.py Cogs, one file per feature set.
│   ├── profile_cog.py
│   ├── streak_cog.py
│   └── achievement_cog.py
├── core/                   # Core business logic and utilities.
│   ├── database.py         # Database connection pool and all query functions.
│   ├── imaging.py          # Image generation logic using Pillow.
│   ├── leveling.py         # XP and level calculation logic.
│   └── (localization.py – i18n 비활성화)
├── (locales/ – 제거)
├── .env                    # Environment variables (NEVER commit).
├── .gitignore
├── requirements.txt        # Project dependencies.
└── main.py                 # Bot entry point: client setup, cog loading.
```

### Import/Dependency Management

- **Dependencies**: All Python dependencies MUST be listed in `requirements.txt`.
- **Import Order**: Imports MUST be grouped in the following order:
    1. Standard library modules (`os`, `asyncio`).
    2. Third-party modules (`discord`, `asyncpg`).
    3. Local application modules (`core.database`, `cogs.profile_cog`).
- **Formatting**: Use `isort` to automatically format imports.
- **Import Style**: Use absolute imports (`from core.database import db`) instead of relative imports.

### Error Handling Patterns

- **Command Errors**: User-facing errors within slash commands MUST be caught. Respond to the user with a clean, localized, and ephemeral message explaining the issue. Do not expose stack traces to the user.
- **Database/API Errors**: All external calls (database, Discord API) MUST be wrapped in `try...except` blocks. Log the full exception for debugging but present a generic error message to the user.
- **Specific Exceptions**: Catch specific exceptions (`asyncpg.PostgresError`) instead of generic `Exception`.

```python
# MUST: Handle specific errors and inform the user clearly.
@app_commands.command(name="profile")
async def profile(self, interaction: discord.Interaction):
    try:
        user_data = await db.fetch_user(interaction.user.id, interaction.guild.id)
        if not user_data:
            await interaction.response.send_message("You are not registered yet.", ephemeral=True)
            return
        # ... generate profile card ...
    except asyncpg.PostgresError as e:
        logging.error(f"Database error in profile command: {e}")
        await interaction.response.send_message("Could not retrieve your profile. Please try again later.", ephemeral=True)
```

## 4. Code Style Rules

### MUST Follow:

1.  **PEP 8 Compliance**: All code MUST adhere to PEP 8 standards. Use `black` for automatic code formatting to ensure consistency.
2.  **Type Hinting**: All function signatures and key variables MUST include type hints. This is critical for code clarity and static analysis in an async environment.
3.  **Asynchronous Operations**: All I/O operations (database queries, API calls, file access) MUST be asynchronous using `async/await`.
4.  **Configuration via Environment Variables**: All secrets (bot token, database URL) MUST be loaded from a `.env` file using `os.getenv()`. Do not hardcode credentials.
5.  **Use f-strings**: For all string formatting, f-strings are the required standard due to their readability and performance.

### MUST NOT Do:

1.  **Do Not Use Blocking Calls**: Never use blocking libraries like `requests` or `time.sleep()` inside an `async` function. Use `aiohttp` for HTTP requests and `asyncio.sleep()` for delays. CPU-intensive tasks like complex image generation should be run in an executor.
2.  **Do Not Write Raw SQL in Command Logic**: All SQL queries MUST be encapsulated within functions in `core/database.py`. This centralizes data access and prevents SQL injection.
3.  **Do Not Use String Formatting for SQL Queries**: Never use f-strings or `%` formatting to insert values into SQL queries. This creates SQL injection vulnerabilities. Always use parameterized queries.
4.  **Do Not Store State in Global Variables**: Avoid using global variables to store user data or session information. The application must be stateless, relying entirely on the database.
5.  **Do Not Create "Helper" or "Util" Dumping Grounds**: Avoid generic modules like `utils.py`. Create modules with specific responsibilities, such as `core/imaging.py` or `core/leveling.py`.

## 5. Architecture Patterns

### Component/Module Structure

- **Cogs for Features**: 각 사용자 기능(예: Profile, Streak)은 자체 Cog 파일에서 구현합니다. (Achievements는 현재 비활성화)
- **Core Logic Separation**: All business logic (database interaction, calculations, image generation) MUST reside in the `/core` directory. Cogs should import and call functions from these core modules. This decouples the Discord API from the core application logic.
- **Database Abstraction**: The `core/database.py` module acts as a data access layer (DAL). It will initialize and manage the `asyncpg` connection pool and provide high-level async functions for all required database operations (e.g., `create_user`, `end_voice_session`).

```python
# MUST: Separate Discord logic (Cog) from database logic (core.database).

# In cogs/profile_cog.py
import discord
from discord.ext import commands
from core import database as db

class ProfileCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="profile")
    async def profile_command(self, interaction: discord.Interaction):
        # The Cog handles the Discord interaction.
        user_stats = await db.fetch_user_stats(interaction.user.id, interaction.guild.id)
        # It calls the database module for data.
        await interaction.response.send_message(f"Your XP: {user_stats['xp']}")

# In core/database.py
import asyncpg

# This module handles all database logic.
async def fetch_user_stats(user_id: int, guild_id: int) -> dict | None:
    pool = get_db_pool() # Assume pool is managed here
    conn = await pool.acquire()
    try:
        query = "SELECT xp, total_seconds FROM users WHERE user_id = $1 AND guild_id = $2"
        # The query and connection details are hidden from the Cog.
        record = await conn.fetchrow(query, user_id, guild_id)
        return dict(record) if record else None
    finally:
        await pool.release(conn)
```

### Data Flow Patterns

- **Command Flow**: `Discord Interaction` -> `Cog Command Handler` -> `Core Database/Logic Function` -> `Return Data` -> `Cog Formats Response` -> `Discord API`.
- **Event Flow**: `Discord Gateway Event (e.g., on_voice_state_update)` -> `Cog Event Listener` -> `Core Database/Logic Function` -> `Database Write`.

### State Management

The database is the only valid place for storing persistent state. The bot's in-memory state should be limited to configuration, the database connection pool, and other non-critical runtime objects.

### API Design (Database Layer)

All SQL queries MUST be parameterized to prevent SQL injection.

```python
# MUST: Use parameterized queries with asyncpg's $1, $2 syntax.
async def update_user_xp(conn, user_id: int, guild_id: int, new_xp: int):
    query = "UPDATE users SET xp = $1 WHERE user_id = $2 AND guild_id = $3"
    await conn.execute(query, new_xp, user_id, guild_id)
```

```python
# MUST NOT: Use f-strings or any other string formatting for queries.
# This is a critical security vulnerability.
async def vulnerable_update_user_xp(conn, user_id: int, guild_id: int, new_xp: int):
    # This code will be rejected in a code review.
    query = f"UPDATE users SET xp = {new_xp} WHERE user_id = {user_id}"
    await conn.execute(query)
```