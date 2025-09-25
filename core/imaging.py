from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import Tuple, Optional
from PIL import Image, ImageDraw, ImageFont, ImageFilter


def seconds_to_hms(seconds: int) -> str:
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    return f"{h:02d}:{m:02d}:{s:02d}"


def seconds_to_hms_ko(seconds: int) -> str:
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    return f"{h}시간 {m}분 {s}초"


def _load_fonts(title_size: int, body_size: int) -> Tuple[ImageFont.FreeTypeFont, ImageFont.FreeTypeFont]:
    """Load Korean-capable fonts with sensible fallbacks.

    Tries project fonts under assets/fonts, then Windows Malgun Gothic, then Arial.
    """
    candidates = [
        Path("assets/fonts/NotoSansKR-Regular.ttf"),
        Path("assets/fonts/NotoSansKR-Regular.otf"),
        Path(r"C:/Windows/Fonts/malgun.ttf"),
        Path(r"C:/Windows/Fonts/malgunbd.ttf"),
        Path("arial.ttf"),
    ]
    title_font = None
    body_font = None
    for p in candidates:
        try:
            if title_font is None:
                title_font = ImageFont.truetype(str(p), title_size)
            if body_font is None:
                body_font = ImageFont.truetype(str(p), body_size)
            if title_font and body_font:
                break
        except Exception:
            continue
    if title_font is None or body_font is None:
        # Final fallback
        title_font = ImageFont.load_default()
        body_font = ImageFont.load_default()
    return title_font, body_font


# (emoji drawing helpers removed; labels render as plain text)

def draw_bold_text(draw: ImageDraw.ImageDraw, x: int, y: int, text: str, font: ImageFont.ImageFont, fill: tuple, strength: int = 1) -> None:
    """Simple bold simulation by overdrawing nearby pixels with the same color."""
    for dx in range(-strength, strength + 1):
        for dy in range(-strength, strength + 1):
            draw.text((x + dx, y + dy), text, fill=fill, font=font)


def render_profile_card(
    username: str,
    level: int,
    xp: int,
    today_seconds: int,
    week_seconds: int,
    month_seconds: int,
    total_seconds: int,
    progress_ratio: float = 0.0,
    xp_in_level: int = 0,
    level_need: int = 1,
    avatar_image: Image.Image | None = None,
    title_text: str | None = None,
    subtitle_line1: str | None = None,
    subtitle_line2: str | None = None,
) -> BytesIO:
    width, height = 800, 360
    # Purple theme (similar to sample)
    background = (222, 210, 255, 255)   # deeper lavender
    card_bg = (201, 182, 255, 255)      # medium lavender
    primary = (131, 96, 195, 255)       # #8360C3
    gold = (231, 185, 96, 255)          # #E7B960
    text = (54, 38, 100, 255)           # dark purple

    img = Image.new("RGBA", (width, height), color=(0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Transparent canvas: skip decorative background texture

    # Fonts (prefer Korean-capable fonts)
    title_font, body_font = _load_fonts(38, 24)

    # Translucent container (no real blur; Discord UI will show through)
    margin = 12
    panel_rect = (margin, margin, width - margin, height - margin)
    glass = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    gdraw = ImageDraw.Draw(glass)
    # Solid purple fill inside the card box (no transparency)
    gdraw.rounded_rectangle(panel_rect, radius=22, fill=(201, 182, 255, 255), outline=(131, 96, 195, 255), width=2)
    img = Image.alpha_composite(img, glass)
    draw = ImageDraw.Draw(img)

    # Header
    draw_bold_text(draw, margin + 24, 16, "학생증", title_font, primary, strength=1)

    # Avatar block on the left (rounded square)
    holder_size = 160
    holder_x = margin + 24
    holder_y = (height - holder_size) // 2
    # Clean avatar holder without visible border
    # (keeping container area for layout, but no stroke)
    # draw.rounded_rectangle omitted for cleaner look
    if avatar_image is not None:
        inner = holder_size - 20
        avatar = avatar_image.convert("RGBA").resize((inner, inner))
        mask = Image.new("L", (inner, inner), 0)
        mdraw = ImageDraw.Draw(mask)
        mdraw.ellipse((0, 0, inner, inner), fill=255)
        img.paste(avatar, (holder_x + (holder_size - inner) // 2, holder_y + (holder_size - inner) // 2), mask)
        # remove colored ring around avatar (no arcs)

    # Right content origin
    right_x = holder_x + holder_size + 32
    # Title: display nickname (fallback: username) with smaller level title on the right
    t_text = title_text or username
    title_y = max(24, holder_y - 20)  # ensure not overlapped vertically
    draw.text((right_x, title_y), t_text, fill=text, font=title_font)
    try:
        from core.leveling import get_level_title  # late import to avoid cycles
        level_title = get_level_title(level)
    except Exception:
        level_title = f"레벨 {level}"
    name_w = draw.textlength(t_text, font=title_font)
    # vertically center the smaller text relative to the big title
    name_bbox = draw.textbbox((right_x, title_y), t_text, font=title_font)
    name_bottom = name_bbox[3] if name_bbox else title_y
    # Align level title's bottom to the name's bottom, then lift slightly for optical alignment
    baseline_offset = -6  # pixels upward
    # draw level title as plain text
    draw.text((right_x + name_w + 12, name_bottom + baseline_offset), level_title, fill=text, font=body_font, anchor="lb")

    # Optional extra lines under the title
    current_bottom = name_bottom
    line_gap = 16
    line_height = 28
    if subtitle_line1:
        line1_y = current_bottom + line_gap
        draw.text((right_x, line1_y), subtitle_line1, fill=text, font=body_font)
        current_bottom = line1_y + line_height
    if subtitle_line2:
        line2_y = current_bottom + line_gap
        draw.text((right_x, line2_y), subtitle_line2, fill=text, font=body_font)
        current_bottom = line2_y + line_height

    # Sections
    # push bars further down if avatar grew or subtitle lines exist, to avoid overlap
    y0 = max(190, holder_y + holder_size - 20, current_bottom + line_gap)
    # Single bar: XP progress only (removed study-time bar)
    bar_x = right_x
    bar_y = y0 + 4
    bar_w = width - bar_x - margin - 24
    bar_h = 26
    under_gap = 8
    draw.rounded_rectangle([(bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h)], radius=8, fill=(232, 224, 214, 255))
    xfill_w = int(bar_w * max(0.0, min(1.0, progress_ratio)))
    if xfill_w > 0:
        draw.rounded_rectangle([(bar_x, bar_y), (bar_x + xfill_w, bar_y + bar_h)], radius=8, fill=primary)
    progress_pct = int(progress_ratio * 100)
    prog_text = f"{xp_in_level}/{max(1, level_need)} XP ({progress_pct}%)"
    xp_font_small = _load_fonts(38, 20)[1]
    t_w = draw.textlength(prog_text, font=xp_font_small)
    draw.text((bar_x + bar_w - t_w, bar_y + bar_h + under_gap), prog_text, fill=text, font=xp_font_small)

    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf


def render_streak_calendar(
    username: str,
    played_dates: set[str],
    today_iso: str,
    primary=(131, 96, 195, 255),
    gold=(231, 185, 96, 255),
    bg=(222, 210, 255, 255),
) -> BytesIO:
    """Render a 7x5 streak calendar for the last 35 days.

    played_dates: set of YYYY-MM-DD strings
    """
    width, height = 800, 360
    cell = 32
    padding = 24
    grid_w = 7 * cell + 6 * 8
    grid_h = 5 * cell + 4 * 8
    img = Image.new("RGBA", (width, height), bg)
    draw = ImageDraw.Draw(img)
    title_font, body_font = _load_fonts(28, 18)

    draw_bold_text(draw, padding, padding, f"{username}의 스트릭", title_font, (54, 38, 100, 255), strength=1)

    # Start from today - 34 days
    from datetime import timedelta, date
    start = date.fromisoformat(today_iso) - timedelta(days=34)

    x0 = padding
    y0 = padding + 42
    idx = 0
    for r in range(5):
        for c in range(7):
            d = start + timedelta(days=idx)
            rect = [x0 + c * (cell + 8), y0 + r * (cell + 8), x0 + c * (cell + 8) + cell, y0 + r * (cell + 8) + cell]
            d_iso = d.isoformat()
            if d_iso in played_dates:
                fill = (231, 185, 96, 255)
            else:
                fill = (210, 196, 244, 255)
            draw.rounded_rectangle(rect, radius=6, fill=fill)
            if d_iso == today_iso:
                draw.rounded_rectangle(rect, radius=6, outline=primary, width=3)
            idx += 1

    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf


def compose_vertical_images(img_top: Image.Image, img_bottom: Image.Image, background=(230, 224, 255, 255), spacing: int = 16) -> BytesIO:
    width = max(img_top.width, img_bottom.width)
    height = img_top.height + spacing + img_bottom.height
    canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    canvas.paste(img_top, (0, 0), img_top)
    canvas.paste(img_bottom, (0, img_top.height + spacing), img_bottom)
    out = BytesIO()
    canvas.save(out, format="PNG")
    out.seek(0)
    return out


def render_stats_and_month_calendar(
    username: str,
    daily: int,
    weekly: int,
    monthly: int,
    total: int,
    year: int,
    month: int,
    played_days: set[int],
    today_day: int | None,
) -> BytesIO:
    """Render left stats and right current month calendar within a shadowed rounded container.
    Ensures day numbers are centered in cells.
    """
    width, height = 800, 360
    bg = (0, 0, 0, 0)
    text = (54, 38, 100, 255)
    primary = (131, 96, 195, 255)
    gold = (231, 185, 96, 255)
    card_bg = (201, 182, 255, 255)
    canvas = Image.new("RGBA", (width, height), bg)
    draw = ImageDraw.Draw(canvas)
    title_font, body_font = _load_fonts(26, 18)

    # Glassmorphism container (purple tint)
    margin = 12
    panel_rect2 = (margin, margin, width - margin, height - margin)
    # No background blur when exporting transparent PNG
    glass2 = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    gdraw2 = ImageDraw.Draw(glass2)
    # Solid purple fill inside the stats/calendar box (no transparency)
    gdraw2.rounded_rectangle(panel_rect2, radius=22, fill=(201, 182, 255, 255), outline=(131, 96, 195, 255), width=2)
    canvas = Image.alpha_composite(canvas, glass2)
    draw = ImageDraw.Draw(canvas)

    pad = margin + 24
    # Headings (swap: Study Day left, Statistics right)
    draw_bold_text(draw, pad, pad, "STUDY DAY", title_font, text, strength=1)
    right_origin = width // 2 + pad // 2
    draw_bold_text(draw, right_origin, pad, "STATISTICS", title_font, text, strength=1)

    # Right stats area
    labels = [
        ("DAILY", seconds_to_hms(daily)[:-3]),
        ("WEEKLY", seconds_to_hms(weekly)[:-3]),
        ("MONTHLY", seconds_to_hms(monthly)[:-3]),
        ("ALL TIME", seconds_to_hms(total)[:-3]),
    ]
    y = pad + 36
    for label, val in labels:
        draw.text((right_origin, y), f"{label}: ", fill=text, font=body_font)
        val_w = draw.textlength(val, font=body_font)
        draw.text((right_origin + 220 - val_w, y), val, fill=text, font=body_font)
        y += 28

    # Right calendar with day numbers centered
    import calendar as _calendar
    cal = _calendar.Calendar(firstweekday=6)
    grid_x = pad
    grid_y = pad + 64  # spacing below heading
    cell_w = 34
    cell_h = 28
    gap_x = 8
    gap_y = 8
    header_h = 20

    month_label = f"{_calendar.month_name[month].upper()} {year}"
    draw.text((grid_x, grid_y - 28), month_label, fill=text, font=body_font)

    # Weekday headers centered above columns
    weekdays = ["S", "M", "T", "W", "T", "F", "S"]
    for i, wd in enumerate(weekdays):
        cx = grid_x + i * (cell_w + gap_x) + cell_w / 2
        cy = grid_y + header_h / 2
        draw.text((cx, cy), wd, fill=text, font=body_font, anchor="mm")

    # Start of grid area
    start_y = grid_y + header_h + gap_y
    for r, week in enumerate(cal.monthdayscalendar(year, month)):
        for c, day in enumerate(week):
            x0 = grid_x + c * (cell_w + gap_x)
            y0 = start_y + r * (cell_h + gap_y)
            if day == 0:
                continue
            rect = (x0, y0, x0 + cell_w, y0 + cell_h)
            fill = (232, 224, 214, 255)
            if day in played_days:
                fill = gold
            draw.rounded_rectangle(rect, radius=6, fill=fill)
            if today_day and day == today_day:
                draw.rounded_rectangle(rect, radius=6, outline=primary, width=2)
            # Center day number exactly in the cell
            cx = x0 + cell_w / 2
            cy = y0 + cell_h / 2
            draw.text((cx, cy), str(day), fill=text, font=body_font, anchor="mm")

    out = BytesIO()
    canvas.save(out, format="PNG")
    out.seek(0)
    return out

