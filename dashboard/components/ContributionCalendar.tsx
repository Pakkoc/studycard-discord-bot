"use client";
import { useMemo, useState } from "react";

export type CalendarDay = { date: string; seconds: number; sessions: number };

type Props = {
  year: number;
  days: CalendarDay[];
  onSelectDate?: (date: string) => void;
  capHours?: number; // optional external cap (e.g., guild-wide max * 0.9)
};

// 월별 최대 색상 정의 (/잔디 명령어와 동일)
const MONTH_COLORS: Record<number, { r: number; g: number; b: number }> = {
  1: { r: 237, g: 1, b: 138 },     // #ED018A
  2: { r: 207, g: 26, b: 27 },     // #CF1A1B
  3: { r: 240, g: 103, b: 48 },    // #F06730
  4: { r: 240, g: 134, b: 34 },    // #F08622
  5: { r: 233, g: 235, b: 40 },    // #E9EB28
  6: { r: 180, g: 231, b: 66 },    // #B4E742
  7: { r: 95, g: 198, b: 80 },     // #5FC650
  8: { r: 31, g: 165, b: 166 },    // #1FA5A6
  9: { r: 27, g: 26, b: 241 },     // #1B1AF1
  10: { r: 65, g: 18, b: 160 },    // #4112A0
  11: { r: 116, g: 29, b: 160 },   // #741DA0
  12: { r: 178, g: 53, b: 147 },   // #B23593
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
  const last = new Date(Date.UTC(year, 11, 31)); // 12월 31일까지만
  // Align to week start (Monday) for GitHub-like layout - 월요일 시작
  const start = new Date(first);
  const firstDayOfWeek = first.getUTCDay(); // 0=일, 1=월, ...
  // 월요일(1)을 기준으로 정렬
  const offset = (firstDayOfWeek + 6) % 7; // 월요일=0, 화요일=1, ... 일요일=6
  start.setUTCDate(first.getUTCDate() - offset);

  const weeks: (string | null)[][] = [];
  for (let d = new Date(start); d <= last || d.getUTCDay() !== 1; d.setUTCDate(d.getUTCDate() + 1)) {
    const iso = d.toISOString().slice(0, 10);
    const widx = Math.floor((d.getTime() - start.getTime()) / (7 * 86400000));
    if (!weeks[widx]) weeks[widx] = [];
    // 해당 연도에 속하지 않는 날은 null로 표시
    const isInYear = d.getUTCFullYear() === year;
    weeks[widx].push(isInYear ? iso : null);
  }

  // 월 레이블 중복 방지를 위한 처리
  const monthLabels = useMemo(() => {
    const labels: (string | null)[] = [];
    let lastMonth = 0;
    weeks.forEach((w) => {
      const firstValidDate = w.find(d => d !== null);
      if (firstValidDate) {
        const d = new Date(firstValidDate);
        const month = d.getUTCMonth() + 1;
        const day = d.getUTCDate();
        // 해당 월의 첫 번째 주에만 레이블 표시 (중복 방지)
        if (month !== lastMonth && day <= 7) {
          labels.push(`${month}월`);
          lastMonth = month;
        } else {
          labels.push(null);
        }
      } else {
        labels.push(null);
      }
    });
    return labels;
  }, [weeks]);

  return (
    <div style={{ display: "flex", gap: 8, marginLeft: 16 }}>
      {/* Y labels - 월요일 시작, 그리드와 정렬 */}
      <div style={{ display: "flex", flexDirection: "column" }}>
        {/* 월 레이블 영역과 높이 맞춤 */}
        <div style={{ height: 18 }} />
        {/* 요일 레이블 */}
        <div style={{ display: "grid", gridTemplateRows: "repeat(7, 14px)", rowGap: 4, color: "#6b7280", fontSize: 12 }}>
          <span>월</span>
          <span>화</span>
          <span>수</span>
          <span>목</span>
          <span>금</span>
          <span>토</span>
          <span>일</span>
        </div>
      </div>
      <div>
        {/* Month labels - 중복 방지 */}
        <div style={{ display: "grid", gridAutoFlow: "column", gridAutoColumns: "14px", columnGap: 4, color: "#6b7280", fontSize: 12, height: 18 }}>
          {monthLabels.map((label, i) => (
            <span key={i} style={{ gridColumn: String(i + 1), whiteSpace: "nowrap" }}>
              {label ?? ""}
            </span>
          ))}
        </div>
        {/* Grid */}
        <div style={{ display: "grid", gridAutoFlow: "column", gridAutoColumns: "14px", columnGap: 4 }}>
          {weeks.map((w, wi) => (
            <div key={wi} style={{ display: "grid", gridTemplateRows: "repeat(7, 14px)", rowGap: 4 }}>
              {w.map((iso, di) => (
                <Cell
                  key={iso ?? `empty-${wi}-${di}`}
                  iso={iso}
                  data={iso ? map.get(iso) : undefined}
                  maxHours={maxHours}
                  onClick={() => iso && onSelectDate?.(iso)}
                />
              ))}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function Cell({ iso, data, maxHours, onClick }: { iso: string | null; data?: CalendarDay; maxHours: number; onClick?: () => void }) {
  // 해당 연도에 존재하지 않는 날은 빈 공간으로 표시
  if (!iso) {
    return <div style={{ width: 14, height: 14 }} />;
  }

  const hours = Math.round(((data?.seconds || 0) / 3600) * 100) / 100;
  const d = new Date(iso);
  const month = d.getUTCMonth() + 1; // 1-12
  // 0시간은 흰색으로 표시 (/잔디 명령어와 동일), 1초 이상이면 월별 색상 적용
  const color = hours <= 0 ? "#ffffff" : intensityColorByMonth(Math.max(0, Math.min(1, hours / maxHours)), month);
  const title = `${iso}\n총 ${hours}시간, ${data?.sessions || 0}세션`;

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
      }}
    />
  );
}

// 월별 색상 적용 (/잔디 명령어와 동일한 7단계 그라데이션)
function intensityColorByMonth(t: number, month: number) {
  const t_raw = Math.max(0, Math.min(1, t));

  // 7단계 그라데이션 적용 (1초 이상이면 최소 1단계 보장)
  // 7단계는 12시간(100%) 이상
  let clamped: number;

  // 100% 이상이면 7단계 (최대 색상)
  if (t_raw >= 1.0) {
    clamped = 1.0;  // 7단계: 12시간 이상
  } else {
    // 1~6단계: 각 단계: 14.29%, 28.57%, 42.86%, 57.14%, 71.43%, 85.71%
    if (t_raw < 0.1429) {
      clamped = 0.1429;  // 1단계: 1초 ~ 1시간 43분 미만
    } else if (t_raw < 0.2857) {
      clamped = 0.2857;  // 2단계: 1시간 43분 ~ 3시간 26분 미만
    } else if (t_raw < 0.4286) {
      clamped = 0.4286;  // 3단계: 3시간 26분 ~ 5시간 9분 미만
    } else if (t_raw < 0.5714) {
      clamped = 0.5714;  // 4단계: 5시간 9분 ~ 6시간 52분 미만
    } else if (t_raw < 0.7143) {
      clamped = 0.7143;  // 5단계: 6시간 52분 ~ 8시간 34분 미만
    } else {
      clamped = 0.8571;  // 6단계: 8시간 34분 ~ 12시간 미만
    }
  }

  // 월별 색상 사용 (/잔디 명령어와 동일)
  const baseColor = MONTH_COLORS[month] || { r: 23, g: 133, b: 12 };

  // Gradient: white to full color
  const r = Math.round(255 + (baseColor.r - 255) * clamped);
  const g = Math.round(255 + (baseColor.g - 255) * clamped);
  const b = Math.round(255 + (baseColor.b - 255) * clamped);
  return `rgb(${r}, ${g}, ${b})`;
}


