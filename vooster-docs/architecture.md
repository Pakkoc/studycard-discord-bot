Of course. Here is the refined, lean, and implementation-focused Technical Requirements Document (TRD) based on the provided PRD.

---

# **Technical Requirements Document (TRD): Discord Silent Study Tracker**

This document outlines the technical specification for building the MVP of the Silent Study Tracker bot. The design prioritizes simplicity, performance within a resource-constrained environment, and rapid implementation.

### **1. Technical Summary**

-   **Core System**: A single, asynchronous Python application using the `discord.py` library.
-   **Function**: The application will listen to Discord Gateway events in real-time to track user voice activity, process slash commands, and serve dynamically generated images.
-   **Data Store**: A managed PostgreSQL database (Supabase) will be used for all data persistence.
-   **Deployment**: The bot will be deployed as a `systemd` service on a single Linux VM (Oracle Cloud Free Tier), ensuring 24/7 operation and automatic restarts on failure.
-   **Key Principle**: Simplicity over complexity. We will avoid unnecessary layers of abstraction, external dependencies, and premature optimization. Features not in the MVP scope, such as a web dashboard or automated email reports, are explicitly excluded from this architecture.

### **2. Core Technology Stack (MVP)**

| Category                  | Technology / Library | Justification                                                                                             |
| ------------------------- | -------------------- | --------------------------------------------------------------------------------------------------------- |
| **Language/Framework**    | **Python 3.11+** / **`discord.py`** | Industry standard for Discord bots. Excellent support for asynchronous operations and API events. |
| **Database**              | **PostgreSQL (Supabase)** | Reliable, free-tier available, and robust enough for the required relational data (users, sessions).      |
| **Database Driver**       | **`asyncpg`**        | A high-performance, direct async driver for PostgreSQL. Avoids the overhead of a heavy ORM like SQLAlchemy for our simple schema. |
| **Image Generation**      | **`Pillow`**         | Powerful and standard library for creating the required profile cards and streak calendars from scratch. |
| **Process Management**    | **`systemd`**        | Standard Linux tool for managing long-running services. Provides logging, auto-restarts, and startup management. |
| **Configuration**         | **`.env` files**     | Standard practice for securely managing secrets like bot tokens and database credentials.              |

**Technologies Explicitly Excluded from MVP:**

-   **Web Framework (FastAPI)**: Not required. The web dashboard is a Phase 2 feature.
-   **ORM (SQLAlchemy/Alembic)**: Over-engineering for the MVP's simple data model. Direct SQL queries via `asyncpg` are more performant and simpler to manage at this scale.
-   **Scheduler (APScheduler)**: Not required. Daily reports are a Phase 2 feature. Any required background tasks can be managed with `asyncio.create_task`.
-   **Charting (matplotlib)**: Overkill. All required visuals can be drawn directly using `Pillow`.

### **3. System Architecture**

The architecture is a simple, monolithic bot application.

#### **3.1. Architectural Diagram**

```mermaid
graph TD
    subgraph Discord
        A[User Voice Activity]
        B[User Slash Commands]
    end

    subgraph "Oracle Cloud VM"
        C{Discord Bot Application (Python/discord.py)}
        C -- Manages Process --> D[systemd]
    end

    subgraph "Supabase Cloud"
        E[PostgreSQL Database]
    end

    A -- Real-time Events --> C
    B -- REST API Calls --> C
    C -- SQL Queries (asyncpg) <--> E
```

#### **3.2. Core Components (Internal Modules)**

1.  **Event Handler**: Listens for `on_voice_state_update` to log the start and end of user voice sessions. This is the core data collection mechanism.
2.  **Command Processor**: Implements slash command handlers (`/profile`, `/streak`).
3.  **Business Logic Service**:
    -   Calculates XP based on voice session duration (1시간 = 1XP).
    -   Determines level-ups using custom thresholds (10단계: 100,150,250,400,600,850,1150,1550,2000).
    -   (업적 시스템 비활성화로 해당 로직 보류)
4.  **Image Generator (`Pillow`)**: A utility module with functions to render user data onto predefined image templates for profile cards and streak calendars. It will load necessary assets (fonts, background images) from a local `/assets` directory.
5.  **Database Client**: A simple data access layer that uses `asyncpg` to connect to the database and execute parameterized SQL queries for all CRUD operations.

#### **3.3. Data Model (Schema)**

The database schema will be kept minimal and indexed for performance.

```sql
-- users: Stores user information and core stats
CREATE TABLE users (
    user_id BIGINT PRIMARY KEY,       -- Discord User ID
    guild_id BIGINT NOT NULL,         -- Server ID
    total_seconds BIGINT DEFAULT 0,
    xp BIGINT DEFAULT 0,
    language VARCHAR(2) DEFAULT 'ko', -- 'ko' or 'en'
    last_seen_at TIMESTAMPTZ,
    UNIQUE(user_id, guild_id)
);

-- voice_sessions: Raw log of every voice session
CREATE TABLE voice_sessions (
    session_id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    guild_id BIGINT NOT NULL,
    started_at TIMESTAMPTZ NOT NULL,
    ended_at TIMESTAMPTZ,
    duration_seconds INT
);

-- daily_streaks: Tracks daily participation for the streak calendar
CREATE TABLE daily_streaks (
    user_id BIGINT NOT NULL,
    guild_id BIGINT NOT NULL,
    streak_date DATE NOT NULL,
    PRIMARY KEY(user_id, guild_id, streak_date)
);

-- (업적 테이블 비활성화, 스키마에서 제거)

-- Create indexes for fast lookups
CREATE INDEX idx_users_guild ON users(guild_id);
CREATE INDEX idx_sessions_user_guild ON voice_sessions(user_id, guild_id);
CREATE INDEX idx_streaks_user_guild ON daily_streaks(user_id, guild_id);
```

### **4. Non-Functional Requirements**

1.  **Performance**: Must process voice state events for up to 1,000 concurrent users without noticeable delay. Database queries for user profiles must complete in under 500ms.
2.  **Availability**: The bot must maintain >99% uptime, achieved via `systemd` auto-restarts and external monitoring (e.g., UptimeRobot).
3.  **Scalability**: All data must be partitioned by `guild_id` to ensure the bot can be added to new servers in the future without data conflicts.
4.  **Security**: The Discord bot token and database connection string must be stored in a `.env` file, which is excluded from version control (`.gitignore`). All database queries will be parameterized to prevent SQL injection.
5.  **Internationalization (i18n)**: (현재 비활성화, `/locales` 및 `users.language` 컬럼 제거)

### **5. Implementation Plan (MVP)**

The 4-week timeline from the PRD is adopted.

-   **Week 1: Foundation & Data Collection**
    -   Initialize project, setup `.env` and `discord.py` bot client.
    -   Write SQL scripts to create the database schema.
    -   Implement the `on_voice_state_update` event handler to start/stop session timers and write to the `voice_sessions` table.

-   **Week 2: Core Logic & Text-Based Commands**
    -   Develop the XP and leveling calculation logic.
    -   Create a text-only `/profile` command that fetches data from the DB and displays it in a Discord embed.
    -   Implement the logic to record daily activity in the `daily_streaks` table.

-   **Week 3: Visualization**
    -   Create image assets (backgrounds, fonts).
    -   Implement the `Pillow`-based image generator for the `/profile` card.
    -   Implement the image generator for the `/streak` calendar.
    -   Integrate image generation into the slash commands.

-   **Week 4: Gamification & Deployment**
    -   Define achievement criteria in code.
    -   Implement the achievement checking logic, triggered after a voice session ends.
    -   Implement the `/achievements` command.
    -   Write the `systemd` service file and deploy the bot to the Oracle VM for beta testing.

### **6. Post-MVP Roadmap (Phase 2+ Considerations)**

The following features are intentionally deferred to simplify the MVP and will be built upon the successful foundation of this TRD:

-   **Administrator Web Dashboard**: Will require adding a web framework (`FastAPI`) and an authentication layer.
-   **Automated Reports**: Will require adding a scheduling library (`APScheduler`) or using cron jobs.
-   **Advanced Caching**: If image generation or DB queries become a bottleneck, a simple in-memory cache (e.g., `dict` with TTL) can be implemented.