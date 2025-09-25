from __future__ import annotations
import os

# Level titles (1..10)
LEVEL_TITLES: list[str] = [
    "마법학도",
    "견습마법사",
    "수습마법사",
    "초급마법사",
    "숙련마법사",
    "중급마법사",
    "상급마법사",
    "정예마법사",
    "대마법사",
    "현자",
]

# XP required for each level-up step (L1->L2, L2->L3, ...)
# Note: Only first 9 steps are used to reach level 10 (현자).
# The provided extra value (2500) is reserved for potential future expansion.
REQUIRED_XP_PER_LEVELUP: list[int] = [
    100, 150, 250, 400, 600, 850, 1150, 1550, 2000,
    # 2500,  # Reserved – not used since max level is 10
]

MAX_LEVEL: int = len(LEVEL_TITLES)


def calculate_xp_gain(duration_seconds: int) -> int:
    """Return XP gain for a finished session.

    Policy: 1 XP per full hour of effective focus time.
    """
    if duration_seconds <= 0:
        return 0
    # Allow override from environment, default to 3600 seconds per XP
    try:
        seconds_per_xp = int(os.getenv("FOCUS_SECONDS_PER_XP", "3600").strip())
    except Exception:
        seconds_per_xp = 3600
    seconds_per_xp = max(1, seconds_per_xp)
    return duration_seconds // seconds_per_xp


def total_xp_required_for_level(level: int) -> int:
    """Total XP required to be AT the given level (1..MAX_LEVEL).

    Level 1 requires 0 total XP. To reach level N, sum the first N-1 steps.
    Values beyond MAX_LEVEL return the cap's total.
    """
    if level <= 1:
        return 0
    if level > MAX_LEVEL:
        level = MAX_LEVEL
    return sum(REQUIRED_XP_PER_LEVELUP[: level - 1])


def calculate_level(total_xp: int) -> int:
    """Convert total XP to a level based on custom step thresholds (cap at MAX_LEVEL)."""
    if total_xp <= 0:
        return 1
    level = 1
    # iterate thresholds until surpassing total_xp or hitting MAX_LEVEL
    while level < MAX_LEVEL and total_xp >= total_xp_required_for_level(level + 1):
        level += 1
    return level


def xp_to_next_level(total_xp: int) -> tuple[int, int]:
    """Return (current_level, xp_needed_for_next_level). If at cap, needed is 0."""
    level = calculate_level(total_xp)
    if level >= MAX_LEVEL:
        return level, 0
    next_total = total_xp_required_for_level(level + 1)
    return level, max(0, next_total - total_xp)


def compute_level_progress(total_xp: int) -> tuple[int, int, int, int, float]:
    """Return (level, xp_in_level, level_total_xp_needed, xp_to_next, progress_ratio).

    - xp_in_level: XP accumulated since reaching current level
    - level_total_xp_needed: XP required to go from current level to next level (0 if capped)
    - xp_to_next: remaining XP to reach next level (0 if capped)
    - progress_ratio: xp_in_level / level_total_xp_needed (0.0~1.0), 1.0 if capped
    """
    level = calculate_level(total_xp)
    prev_total = total_xp_required_for_level(level)
    if level >= MAX_LEVEL:
        # at cap
        xp_in_level = max(0, total_xp - prev_total)
        return level, xp_in_level, 0, 0, 1.0

    next_total = total_xp_required_for_level(level + 1)
    xp_in_level = max(0, total_xp - prev_total)
    level_need = max(1, next_total - prev_total)
    xp_to_next = max(0, next_total - total_xp)
    progress = min(1.0, xp_in_level / level_need)
    return level, xp_in_level, level_need, xp_to_next, progress


def get_level_title(level: int) -> str:
    """Return the Korean title for a given level (1..MAX_LEVEL)."""
    if level < 1:
        level = 1
    if level > MAX_LEVEL:
        level = MAX_LEVEL
    return LEVEL_TITLES[level - 1]

