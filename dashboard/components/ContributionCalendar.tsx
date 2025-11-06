"use client";
import { useMemo, useState } from "react";

export type CalendarDay = { date: string; seconds: number; sessions: number };

type Props = {
  year: number;
  days: CalendarDay[];
  onSelectDate?: (date: string) => void;
  capHours?: number; // optional external cap (e.g., guild-wide max * 0.9)
};

export default function ContributionCalendar({ year, days, onSelectDate, capHours }: Props) {
  const map = useMemo(() => {
    const m = new Map<string, CalendarDay>();
    for (const d of days) m.set(d.date, d);
    return m;
  }, [days]);

  // Use robust cap: ~95th percentile of daily hours to avoid outlier dominance
  const maxHours = useMemo(() => {
    const hs = days
      .map((d) => Math.round(((d.seconds || 0) / 3600) * 100) / 100)
      .filter((h) => h > 0)
      .sort((a, b) => a - b);
    if (hs.length === 0) return 1;
    if (capHours && capHours > 0) return capHours;
    const idx = Math.max(0, Math.floor(hs.length * 0.95) - 1);
    const p95 = hs[idx] ?? hs[hs.length - 1];
    return Math.max(p95, 1);
  }, [days, capHours]);

  const first = new Date(Date.UTC(year, 0, 1));
  const last = new Date(Date.UTC(year + 1, 0, 1));
  // Align to week start (Sunday) for GitHub-like layout
  const start = new Date(first);
  start.setUTCDate(first.getUTCDate() - first.getUTCDay());
  const weeks: string[][] = [];
  for (let d = new Date(start); d < last || d.getUTCDay() !== 0; d.setUTCDate(d.getUTCDate() + 1)) {
    const iso = d.toISOString().slice(0, 10);
    const widx = Math.floor((d.getTime() - start.getTime()) / (7 * 86400000));
    if (!weeks[widx]) weeks[widx] = [];
    weeks[widx].push(iso);
  }

  return (
    <div style={{ display: "flex", gap: 12 }}>
      {/* Y labels */}
      <div style={{ display: "grid", gridTemplateRows: "repeat(7, 14px)", rowGap: 4, marginTop: 20, color: "#6b7280", fontSize: 12 }}>
        <span>월</span>
        <span>화</span>
        <span>수</span>
        <span>목</span>
        <span>금</span>
        <span>토</span>
        <span>일</span>
      </div>
      <div>
        {/* Month labels */}
        <div style={{ display: "grid", gridAutoFlow: "column", gridAutoColumns: "14px", columnGap: 4, color: "#6b7280", fontSize: 12, marginLeft: 2 }}>
          {weeks.map((w, i) => (
            <span key={i} style={{ gridColumn: String(i + 1) }}>
              {monthLabel(w[0])}
            </span>
          ))}
        </div>
        {/* Grid */}
        <div style={{ display: "grid", gridAutoFlow: "column", gridAutoColumns: "14px", columnGap: 4, marginTop: 4 }}>
          {weeks.map((w, wi) => (
          <div key={wi} style={{ display: "grid", gridTemplateRows: "repeat(7, 14px)", rowGap: 4 }}>
              {([...w.slice(1, 7), w[0]]).map((iso) => (
                <Cell key={iso} iso={iso} data={map.get(iso)} maxHours={maxHours} onClick={() => onSelectDate?.(iso)} />
              ))}
            </div>
          ))}
        </div>
      </div>
      {/* Legend vertical (많음 → 적음) */}
      <div style={{ display: "grid", gridTemplateRows: "auto 112px auto", rowGap: 6, color: "#6b7280", fontSize: 12 }}>
        <span style={{ textAlign: "center" }}>많음</span>
        <div style={{ width: 12, height: 112, borderRadius: 2, border: "1px solid #e5e7eb", background: "linear-gradient(to bottom, #ed008c, #d0191b, #f06730, #f08622, #e9eb28, #b4e742, #5fc650, #1fa5a6, #761ca2, #b23593)" }} />
        <span style={{ textAlign: "center" }}>적음</span>
      </div>
    </div>
  );
}

function Cell({ iso, data, maxHours, onClick }: { iso: string; data?: CalendarDay; maxHours: number; onClick?: () => void }) {
  const hours = Math.round(((data?.seconds || 0) / 3600) * 100) / 100;
  const d = new Date(iso);
  const month = d.getUTCMonth() + 1;
  const color = hours <= 0 ? "#e5e7eb" : intensityColor(Math.max(0, Math.min(1, hours / maxHours)), month);
  const title = `${iso}\n총 ${hours}시간, ${data?.sessions || 0}세션`;
  const inYear = true; // we include prev/next spillover weeks like GitHub
  return (
    <div
      role="button"
      title={title}
      onClick={onClick}
      aria-label={title}
      style={{
        width: 14,
        height: 14,
        borderRadius: 3,
        background: color,
        // Make blanks and light tones visible across themes
        boxShadow: "inset 0 0 0 1px #d1d5db",
        cursor: "pointer",
        opacity: inYear ? 1 : 0.35,
      }}
    />
  );
}

function monthLabel(iso?: string) {
  if (!iso) return "";
  const d = new Date(iso);
  const m = d.getUTCMonth() + 1;
  // Show label only on the first week of a month
  return d.getUTCDate() <= 7 ? `${m}월` : "";
}

function LegendBox({ color }: { color: string }) {
  return <span style={{ width: 12, height: 12, background: color, display: "inline-block", borderRadius: 2, border: "1px solid #e5e7eb" }} />;
}

function intensityColor(t: number, month: number) {
  const clamped = Math.max(0, Math.min(1, t));
  
  // Monthly color scheme
  const monthColors: { [key: number]: { r: number; g: number; b: number } } = {
    1: { r: 237, g: 1, b: 138 },      // January #ED018A
    2: { r: 207, g: 26, b: 27 },      // February #CF1A1B
    3: { r: 240, g: 103, b: 48 },     // March #F06730
    4: { r: 240, g: 134, b: 34 },     // April #F08622
    5: { r: 233, g: 235, b: 40 },     // May #E9EB28
    6: { r: 180, g: 231, b: 66 },     // June #B4E742
    7: { r: 95, g: 198, b: 80 },      // July #5FC650
    8: { r: 31, g: 165, b: 166 },     // August #1FA5A6
    9: { r: 27, g: 26, b: 241 },      // September #1B1AF1
    10: { r: 65, g: 18, b: 160 },     // October #4112A0
    11: { r: 116, g: 29, b: 160 },    // November #741DA0
    12: { r: 178, g: 53, b: 147 },    // December #B23593
  };
  
  const end = monthColors[month] || { r: 23, g: 133, b: 12 }; // fallback to green
  // Full gradient: white (t=0) to full color (t=1)
  const r = Math.round(255 + (end.r - 255) * clamped);
  const g = Math.round(255 + (end.g - 255) * clamped);
  const b = Math.round(255 + (end.b - 255) * clamped);
  return `rgb(${r}, ${g}, ${b})`;
}


