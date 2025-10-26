"use client";
import { useMemo, useState } from "react";

export type CalendarDay = { date: string; seconds: number; sessions: number };

type Props = {
  year: number;
  days: CalendarDay[];
  onSelectDate?: (date: string) => void;
};

export default function ContributionCalendar({ year, days, onSelectDate }: Props) {
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
    const idx = Math.max(0, Math.floor(hs.length * 0.95) - 1);
    const p95 = hs[idx] ?? hs[hs.length - 1];
    return Math.max(p95, 1);
  }, [days]);

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
        <span>일</span>
        <span></span>
        <span>화</span>
        <span></span>
        <span>목</span>
        <span></span>
        <span>토</span>
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
              {w.map((iso) => (
                <Cell key={iso} iso={iso} data={map.get(iso)} maxHours={maxHours} onClick={() => onSelectDate?.(iso)} />
              ))}
            </div>
          ))}
        </div>
      </div>
      {/* Legend vertical (많음 → 적음) */}
      <div style={{ display: "grid", gridTemplateRows: "auto 112px auto", rowGap: 6, color: "#6b7280", fontSize: 12 }}>
        <span style={{ textAlign: "center" }}>많음</span>
        <div style={{ width: 12, height: 112, borderRadius: 2, border: "1px solid #e5e7eb", background: "linear-gradient(#2563eb, #dbeafe, #e5e7eb)" }} />
        <span style={{ textAlign: "center" }}>적음</span>
      </div>
    </div>
  );
}

function Cell({ iso, data, maxHours, onClick }: { iso: string; data?: CalendarDay; maxHours: number; onClick?: () => void }) {
  const hours = Math.round(((data?.seconds || 0) / 3600) * 100) / 100;
  const color = hours <= 0 ? "#e5e7eb" : intensityColor(Math.max(0, Math.min(1, hours / maxHours)));
  const title = `${iso}\n총 ${hours}시간, ${data?.sessions || 0}세션`;
  const inYear = true; // we include prev/next spillover weeks like GitHub
  return (
    <div
      role="button"
      title={title}
      onClick={onClick}
      aria-label={title}
      style={{ width: 14, height: 14, borderRadius: 3, background: color, cursor: "pointer", opacity: inYear ? 1 : 0.35 }}
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

function intensityColor(t: number) {
  const clamped = Math.max(0, Math.min(1, t));
  const start = { r: 219, g: 234, b: 254 }; // blue-100
  const end = { r: 37, g: 99, b: 235 }; // blue-600
  const r = Math.round(start.r + (end.r - start.r) * clamped);
  const g = Math.round(start.g + (end.g - start.g) * clamped);
  const b = Math.round(start.b + (end.b - start.b) * clamped);
  return `rgb(${r}, ${g}, ${b})`;
}


