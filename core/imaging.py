from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import Tuple, Optional
import unicodedata
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# Simple emoji/symbol replacement map to ensure stable rendering with monochrome glyphs
# Example: replace color emoji (not reliably supported by Pillow) with safe symbols
_SYMBOL_REPLACEMENTS: dict[str, str] = {
    # Optional single-character replacements before final stripping
    # (kept for future use; current policy strips all symbols/emojis)
}


def _hex_to_rgb(value: str) -> tuple[int, int, int]:
    h = value.strip().lstrip("#")
    if len(h) != 6:
        raise ValueError(f"Invalid hex color: {value}")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _mix_rgb(color: tuple[int, int, int], target: tuple[int, int, int], ratio: float) -> tuple[int, int, int]:
    ratio = max(0.0, min(1.0, ratio))
    return tuple(int(c * (1.0 - ratio) + t * ratio) for c, t in zip(color, target))


def _relative_luminance(color: tuple[int, int, int]) -> float:
    def channel(v: int) -> float:
        x = v / 255.0
        return x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4

    r, g, b = (channel(v) for v in color)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


_HOUSE_THEME_BASES: dict[str, str] = {
    "소용돌이": "#FBE3ED",
    "노블레빗": "#E8DDFF",
    "볼리베어": "#D2E7FE",
    "팽도리아": "#D7D9E2",
    "펭도리야": "#D7D9E2",
}


_DEFAULT_THEME: dict[str, tuple[int, int, int, int]] = {
    "background": (222, 210, 255, 255),
    "card": (201, 182, 255, 255),
    "outline": (131, 96, 195, 255),
    "primary": (131, 96, 195, 255),
    "text": (54, 38, 100, 255),
    "bar_bg": (232, 224, 214, 255),
    "accent": (231, 185, 96, 255),
}


def _resolve_house_theme(house_name: str | None) -> dict[str, tuple[int, int, int, int]]:
    if not house_name:
        return _DEFAULT_THEME
    key = house_name.strip()
    if not key:
        return _DEFAULT_THEME
    base_hex = _HOUSE_THEME_BASES.get(key.lower()) or _HOUSE_THEME_BASES.get(key)
    if not base_hex:
        return _DEFAULT_THEME

    base_rgb = _hex_to_rgb(base_hex)
    background = (*base_rgb, 255)
    card_rgb = _mix_rgb(base_rgb, (255, 255, 255), 0.18)
    outline_rgb = _mix_rgb(base_rgb, (0, 0, 0), 0.25)
    primary_rgb = _mix_rgb(base_rgb, (0, 0, 0), 0.3)
    bar_rgb = _mix_rgb(card_rgb, (255, 255, 255), 0.2)

    text_rgb = (42, 32, 68)
    if _relative_luminance(card_rgb) < 0.35:
        text_rgb = (240, 238, 245)

    return {
        "background": background,
        "card": (*card_rgb, 255),
        "outline": (*outline_rgb, 255),
        "primary": (*primary_rgb, 255),
        "text": (*text_rgb, 255),
        "bar_bg": (*bar_rgb, 255),
        "accent": _DEFAULT_THEME["accent"],
    }


def _strip_symbols_emojis(text: str) -> str:
    """Remove emoji/symbol-like characters to avoid rendering issues.

    Heuristics:
    - Remove all Unicode category 'S*' (symbols)
    - Remove common emoji ranges (U+1F000–U+1FAFF, U+2600–U+26FF, U+2700–U+27BF)
    - Remove variation selectors (U+FE0E/U+FE0F) and ZWJ (U+200D)
    """
    out_chars: list[str] = []
    for ch in text:
        cp = ord(ch)
        cat = unicodedata.category(ch)
        if cat.startswith("S"):
            continue
        if 0x1F000 <= cp <= 0x1FAFF:
            continue
        if 0x2600 <= cp <= 0x26FF:
            continue
        if 0x2700 <= cp <= 0x27BF:
            continue
        if cp in (0xFE0E, 0xFE0F, 0x200D):  # VS15/VS16, ZWJ
            continue
        out_chars.append(ch)
    return "".join(out_chars)


def _sanitize_text_render(text: str | None) -> str | None:
    if text is None:
        return None
    for src, dst in _SYMBOL_REPLACEMENTS.items():
        text = text.replace(src, dst)
    return _strip_symbols_emojis(text)


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
        # Common Linux paths (server) – try CJK first
        Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
        Path("/usr/share/fonts/truetype/noto/NotoSansKR-Regular.ttf"),
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


def _load_symbol_font(size: int) -> Optional[ImageFont.FreeTypeFont]:
    """Load a fallback font that covers miscellaneous symbols/emoji (mono)."""
    symbol_candidates = [
        Path("assets/fonts/NotoSansSymbols2-Regular.ttf"),
        Path("assets/fonts/DejaVuSans.ttf"),
        Path("/usr/share/fonts/truetype/noto/NotoSansSymbols2-Regular.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    ]
    for p in symbol_candidates:
        try:
            return ImageFont.truetype(str(p), size)
        except Exception:
            continue
    return None


def _draw_text_with_symbol_fallback(
    draw: ImageDraw.ImageDraw,
    xy: Tuple[int, int],
    text: str,
    primary_font: ImageFont.FreeTypeFont,
    fill: Tuple[int, int, int, int],
    size_for_fallback: int,
) -> None:
    """Draw text char-by-char using a symbol-capable fallback font for 'So' category.

    Notes:
    - This is a pragmatic fallback to render characters like \u2610 (ballot box) that
      NotoSansKR가 포함하지 않는 경우를 대비합니다.
    - 컬러 이모지는 Pillow에서 제한적이므로 흑백 글리프 폰트(예: NotoSansSymbols2/DejaVuSans)를 사용합니다.
    """
    x, y = xy
    fallback = _load_symbol_font(size_for_fallback)
    for ch in text:
        use_fallback = fallback is not None and unicodedata.category(ch).startswith("S")
        font = fallback if use_fallback else primary_font
        # advance width
        try:
            w = int(font.getlength(ch))  # Pillow>=8
        except Exception:
            w = font.getsize(ch)[0]
        draw.text((x, y), ch, fill=fill, font=font)
        x += w


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
    house_name: str | None = None,
    voost_visible: bool = True,
) -> BytesIO:
    width, height = 800, 360
    theme = _resolve_house_theme(house_name)
    background = theme["background"]
    card_bg = theme["card"]
    primary = theme["primary"]
    text = theme["text"]
    outline = theme["outline"]
    bar_bg = theme["bar_bg"]

    img = Image.new("RGBA", (width, height), color=background)
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
    gdraw.rounded_rectangle(panel_rect, radius=22, fill=card_bg, outline=outline, width=2)
    img = Image.alpha_composite(img, glass)
    draw = ImageDraw.Draw(img)

    # Header
    # Header title
    header_text = "학생증"
    header_x = margin + 24
    header_y = 16
    header_bold_strength = 1
    draw_bold_text(draw, header_x, header_y, header_text, title_font, primary, strength=header_bold_strength)
    # Attach optional voost icon only when allowed
    if voost_visible:
        try:
            voost_candidates = [
                Path("image/voost.png"),
                Path("image/@voost.png"),
                Path("assets/voost.png"),
                Path("assets/@voost.png"),
                Path("assets/images/voost.png"),
                Path("assets/images/@voost.png"),
            ]
            voost_path = next((p for p in voost_candidates if p.exists()), None)
            if voost_path is not None:
                vb = draw.textbbox((header_x, header_y), header_text, font=title_font)
                text_w = (vb[2] - vb[0]) if vb else int(draw.textlength(header_text, font=title_font))
                text_h = (vb[3] - vb[1]) if vb else 32
                icon = Image.open(voost_path).convert("RGBA")
                try:
                    alpha_ch = icon.split()[3]
                    bbox = alpha_ch.getbbox()
                    if bbox:
                        icon = icon.crop(bbox)
                except Exception:
                    pass
                target_h = max(18, int(text_h * 1.00))
                scale = target_h / float(icon.height)
                target_w = max(18, int(icon.width * scale))
                icon = icon.resize((target_w, target_h), Image.LANCZOS)
                vis_top = header_y - header_bold_strength
                vis_bottom = header_y + text_h + header_bold_strength
                center_y = (vis_top + vis_bottom) / 2.0
                gap = 4
                ix = int(round(header_x + text_w + gap))
                nudge_y = 13
                iy = int(round(center_y - target_h / 2.0 + nudge_y))
                try:
                    glow = Image.new("RGBA", icon.size, (primary[0], primary[1], primary[2], 90))
                    glow.putalpha(icon.split()[3])
                    glow = glow.filter(ImageFilter.GaussianBlur(1.2))
                    img.paste(glow, (ix, iy), glow)
                except Exception:
                    pass
                img.paste(icon, (ix, iy), icon)
        except Exception:
            pass

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
    # Sanitize: strip emojis/symbols before rendering
    t_text = _sanitize_text_render(title_text or username) or ""
    title_y = max(24, holder_y - 20)  # ensure not overlapped vertically
    # Draw title (nickname) with symbol fallback for characters not covered by KR font
    _draw_text_with_symbol_fallback(draw, (right_x, title_y), t_text, title_font, text, 38)
    try:
        from core.leveling import get_level_title  # late import to avoid cycles
        level_title = get_level_title(level)
    except Exception:
        level_title = f"레벨 {level}"
    # Compute width considering fallback glyphs
    try:
        fb = _load_symbol_font(38)
        name_w = 0
        for ch in t_text:
            use_fb = fb is not None and unicodedata.category(ch).startswith("S")
            f = fb if use_fb else title_font
            name_w += int(f.getlength(ch))
    except Exception:
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
    subtitle_line1 = _sanitize_text_render(subtitle_line1)
    subtitle_line2 = _sanitize_text_render(subtitle_line2)
    if subtitle_line1:
        line1_y = current_bottom + line_gap
        _draw_text_with_symbol_fallback(draw, (right_x, line1_y), subtitle_line1, body_font, text, 24)
        current_bottom = line1_y + line_height
    if subtitle_line2:
        line2_y = current_bottom + line_gap
        _draw_text_with_symbol_fallback(draw, (right_x, line2_y), subtitle_line2, body_font, text, 24)
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
    # Track color: slightly darker than card for contrast, with subtle border
    card_rgb = (card_bg[0], card_bg[1], card_bg[2])
    track_rgb = _mix_rgb(card_rgb, (0, 0, 0), 0.15)
    track = (*track_rgb, 255)
    border_rgb = _mix_rgb(track_rgb, (255, 255, 255), 0.15)
    border = (*border_rgb, 255)
    white = (255, 255, 255, 255)

    # Always show full-length track with outline for 0% readability
    draw.rounded_rectangle([(bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h)], radius=8, fill=track, outline=border, width=1)

    # Filled portion in white
    xfill_w = int(bar_w * max(0.0, min(1.0, progress_ratio)))
    if xfill_w > 0:
        draw.rounded_rectangle([(bar_x, bar_y), (bar_x + xfill_w, bar_y + bar_h)], radius=8, fill=white)
        # Golden end-dot for focus
        end_x = min(bar_x + xfill_w, bar_x + bar_w - 2)
        cy = bar_y + bar_h // 2
        r = 3
        dot_rect = (end_x - r, cy - r, end_x + r, cy + r)
        draw.ellipse(dot_rect, fill=theme["accent"])

    # Progress label: inside when >=40%, else to the right (fallback below if tight)
    progress_pct = int(progress_ratio * 100)
    prog_text = f"{xp_in_level}/{max(1, level_need)} XP ({progress_pct}%)"
    xp_font_small = _load_fonts(38, 20)[1]
    t_w = draw.textlength(prog_text, font=xp_font_small)
    t_bbox = draw.textbbox((0, 0), prog_text, font=xp_font_small)
    t_h = (t_bbox[3] - t_bbox[1]) if t_bbox else 14
    placed = False  # do not place progress text inside the bar; render outside only
    # Always render outside the bar: prefer right side; otherwise below (original position)
    # Try to place to the right of the bar; clamp within canvas
    tx = min(width - margin - t_w, bar_x + bar_w + 8)
    ty = bar_y + (bar_h - t_h) // 2
    if tx > bar_x + bar_w + 2:
        draw.text((tx, ty), prog_text, fill=text, font=xp_font_small)
        placed = True
    if not placed:
        # Fallback: below the bar (original position)
        draw.text((bar_x + bar_w - t_w, bar_y + bar_h + under_gap), prog_text, fill=text, font=xp_font_small)

    # (moved watermark to stats panel for visual balance)

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
    house_name: str | None = None,
) -> BytesIO:
    """Render left stats and right current month calendar within a shadowed rounded container.
    Ensures day numbers are centered in cells.
    """
    width, height = 800, 360
    theme = _resolve_house_theme(house_name)
    bg = theme["background"]
    text = theme["text"]
    primary = theme["primary"]
    accent = theme["accent"]
    card_bg = theme["card"]
    outline = theme["outline"]
    neutral = theme["bar_bg"]
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
    gdraw2.rounded_rectangle(panel_rect2, radius=22, fill=card_bg, outline=outline, width=2)
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
            fill = neutral
            if day in played_days:
                fill = accent
            draw.rounded_rectangle(rect, radius=6, fill=fill)
            if today_day and day == today_day:
                draw.rounded_rectangle(rect, radius=6, outline=primary, width=2)
            # Center day number exactly in the cell
            cx = x0 + cell_w / 2
            cy = y0 + cell_h / 2
            draw.text((cx, cy), str(day), fill=text, font=body_font, anchor="mm")

    # Watermark inside the dashed box area (right column bottom rectangle)
    try:
        candidates = [
            Path("image/impress.png"),
            Path("assets/@impress.png"),
            Path("assets/impress.png"),
            Path("assets/images/@impress.png"),
            Path("assets/images/impress.png"),
        ]
        wm_path = next((p for p in candidates if p.exists()), None)
        if wm_path is not None:
            wm = Image.open(wm_path).convert("RGBA")
            # Define target box: within right column, below stats lines and above bottom
            inner_margin = 12
            area_left = right_origin + inner_margin
            area_right = width - pad - inner_margin
            # 'y' holds the last used Y for stats rows (after loop above)
            stats_bottom = y
            area_top = stats_bottom + 16
            area_bottom = height - pad - inner_margin
            area_w = max(1, area_right - area_left)
            area_h = max(1, area_bottom - area_top)

            # Scale watermark to fit inside area with a small padding factor
            scale_w = area_w / float(wm.width)
            scale_h = area_h / float(wm.height)
            scale = min(scale_w, scale_h, 1.0) * 0.96
            if scale < 1.0:
                new_w = max(1, int(wm.width * scale))
                new_h = max(1, int(wm.height * scale))
                wm = wm.resize((new_w, new_h), Image.LANCZOS)
            # Center inside the target area
            pos_x = area_left + (area_w - wm.width) // 2
            pos_y = area_top + (area_h - wm.height) // 2
            canvas.alpha_composite(wm, (pos_x, pos_y))
    except Exception:
        pass

    out = BytesIO()
    canvas.save(out, format="PNG")
    out.seek(0)
    return out


def render_annual_grass_image(
    username: str,
    year: int,
    days: list[tuple[str, int]],  # (YYYY-MM-DD, seconds)
    cap_hours: float,
    title: str | None = None,
    house_name: str | None = None,
    avatar_image: Image.Image | None = None,
) -> BytesIO:
    """Render a GitHub-like annual contribution calendar image.

    - Day boundary is assumed already adjusted (e.g., KST+06) in input dates.
    - Color scale: 0h -> #e5e7eb, then linear gradient blue-100 -> blue-600 by hours/cap.
    """
    # Prepare map date -> hours
    seconds_map: dict[str, int] = {d: int(s) for d, s in days}
    hours_map: dict[str, float] = {d: round((s / 3600.0), 2) for d, s in seconds_map.items()}

    # Layout constants
    cell = 14
    gap = 4
    left_label_w = 28
    outer_margin = 12
    panel_pad = 18

    # Build full date grid aligned to Sunday start
    import datetime as _dt
    jan1 = _dt.date(year, 1, 1)
    jan1_dow = (jan1.weekday() + 1) % 7  # Sunday=0
    start = jan1 - _dt.timedelta(days=jan1_dow)
    next_jan = _dt.date(year + 1, 1, 1)

    # Iterate days to build weeks
    weeks: list[list[str]] = []
    d = start
    while d < next_jan or d.weekday() != 6:  # until Sunday after year end
        iso = d.isoformat()
        widx = (d - start).days // 7
        if len(weeks) <= widx:
            weeks.append([])
        weeks[widx].append(iso)
        d += _dt.timedelta(days=1)

    cols = len(weeks)
    # Use 7 rows: Monday(0) ~ Saturday(5) with Sunday as last row for clarity
    rows = 7
    grid_w = cols * cell + (cols - 1) * gap
    grid_h = rows * cell + (rows - 1) * gap

    # Fonts (load early to size header dynamically)
    title_font, body_font = _load_fonts(18, 12)
    # Title text to measure header height
    title_text = title or f"{username} · {year} 연간 잔디"
    # Measure title height safely (fallback to font size on error)
    try:
        _tmp = Image.new("RGB", (1, 1))
        _tdraw = ImageDraw.Draw(_tmp)
        tb = _tdraw.textbbox((0, 0), title_text, font=title_font)
        title_h = max(0, (tb[3] - tb[1])) if tb else 18
    except Exception:
        title_h = 18
    # Dynamic header height with breathing room
    header_h = max(44, title_h + 14)

    width = outer_margin * 2 + panel_pad * 2 + left_label_w + grid_w
    height = outer_margin * 2 + panel_pad * 2 + header_h + grid_h

    # Themed card background
    theme = _resolve_house_theme(house_name)
    bg = theme["background"]
    card_bg = theme["card"]
    outline = theme["outline"]
    text_color = theme["text"]
    # Derive subtle cell border colors from card background for consistent contrast
    card_rgb = (card_bg[0], card_bg[1], card_bg[2])
    cell_border_rgb = _mix_rgb(card_rgb, (0, 0, 0), 0.12)
    empty_border_rgb = _mix_rgb(card_rgb, (0, 0, 0), 0.18)

    img = Image.new("RGBA", (width, height), bg)
    draw = ImageDraw.Draw(img)

    # Card container
    panel_rect = (outer_margin, outer_margin, width - outer_margin, height - outer_margin)
    g = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    gdraw = ImageDraw.Draw(g)
    gdraw.rounded_rectangle(panel_rect, radius=20, fill=card_bg, outline=outline, width=2)
    img = Image.alpha_composite(img, g)
    draw = ImageDraw.Draw(img)

    # Title (inside card header) with small avatar aligned to text height
    # 프로필 이미지 + 제목 위치 조정
    header_x = outer_margin + panel_pad + 20  # Move title and avatar 20px to the right
    header_y = outer_margin + panel_pad - 12  # Move title and avatar 10px up
    text_h_for_icon = title_h  # measured earlier
    icon_gap = 6
    header_x_text = header_x
    if avatar_image is not None:
        try:
            icon = avatar_image.convert("RGBA")
            # icon size proportional to text height, visually small
            target_h = max(16, min(28, int(round(text_h_for_icon * 0.9))))
            target_w = target_h
            if icon.height != target_h or icon.width != target_w:
                icon = icon.resize((target_w, target_h), Image.LANCZOS)
            # circular mask
            mask = Image.new("L", (target_w, target_h), 0)
            mdraw = ImageDraw.Draw(mask)
            mdraw.ellipse((0, 0, target_w, target_h), fill=255)
            # y to align with text baseline (lower than center)
            iy = int(round(header_y + text_h_for_icon - target_h + 3))
            ix = header_x
            img.paste(icon, (ix, iy), mask)
            # subtle border for clarity on light backgrounds
            bdraw = ImageDraw.Draw(img)
            bcolor = (*_mix_rgb((card_bg[0], card_bg[1], card_bg[2]), (0, 0, 0), 0.18), 255)
            bdraw.ellipse((ix, iy, ix + target_w, iy + target_h), outline=bcolor, width=1)
            header_x_text = header_x + target_w + icon_gap
        except Exception:
            header_x_text = header_x
    draw.text((header_x_text, header_y), title_text, fill=text_color, font=title_font)

    # Weekday labels: Monday at top, Sunday at bottom
    y_labels = ["월", "화", "수", "목", "금", "토", "일"]
    for i, lab in enumerate(y_labels):
        x = outer_margin + panel_pad + 2
        y = outer_margin + panel_pad + header_h + i * (cell + gap) + (cell - 12) // 2 - 3
        draw.text((x, y), lab, fill=(107, 114, 128, 255), font=body_font)

    # Month labels per column using first day in that week
    def _month_label(iso: str) -> str:
        if not iso:
            return ""
        d = _dt.date.fromisoformat(iso)
        return f"{d.month}월" if d.day <= 7 else ""

    # Place month labels near the bottom of the header area to avoid title overlap
    month_label_y = outer_margin + panel_pad + header_h - 18  # approx. body font height
    for c, w in enumerate(weeks):
        label = _month_label(w[0] if w else "")
        if label:
            lx = outer_margin + panel_pad + left_label_w + c * (cell + gap)
            draw.text((lx, month_label_y), label, fill=(107, 114, 128, 255), font=body_font)

    # Draw cells
    def _intensity_color(hours: float) -> tuple[int, int, int, int]:
        if hours <= 0:
            return (229, 231, 235, 255)  # #e5e7eb (empty cells - light gray)
        t = max(0.0, min(1.0, hours / max(1e-6, cap_hours)))
        # Green gradient: light green -> dark green (#17850c)
        start_rgb = (200, 230, 210)  # light green (improved visibility)
        end_rgb = (23, 133, 12)      # #17850c (dark green)
        r = int(round(start_rgb[0] + (end_rgb[0] - start_rgb[0]) * t))
        g = int(round(start_rgb[1] + (end_rgb[1] - start_rgb[1]) * t))
        b = int(round(start_rgb[2] + (end_rgb[2] - start_rgb[2]) * t))
        return (r, g, b, 255)

    for c, w in enumerate(weeks):
        # Each week is Sunday..Saturday; order as Mon..Sat then Sun (bottom row)
        ordered = w[1:7] + [w[0]]
        for r, iso in enumerate(ordered):
            hours = float(hours_map.get(iso, 0.0))
            color = _intensity_color(hours)
            border = (* (empty_border_rgb if hours <= 0.0 else cell_border_rgb), 255)
            x0 = outer_margin + panel_pad + left_label_w + c * (cell + gap)
            y0 = outer_margin + panel_pad + header_h + r * (cell + gap)
            draw.rounded_rectangle((x0, y0, x0 + cell, y0 + cell), radius=3, fill=color, outline=border, width=1)

    out = BytesIO()
    img.save(out, format="PNG")
    out.seek(0)
    return out
