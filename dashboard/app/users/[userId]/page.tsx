import LineChart from "@/components/LineChart";
import Heatmap from "@/components/Heatmap";
import ContributionCalendar from "@/components/ContributionCalendar";
import CircularHeatmap from "@/components/CircularHeatmap";
import EnergyCurve from "@/components/EnergyCurve";
import {
  fetchUserDetail,
  fetchUserEntryLogs,
  fetchUserDailyTrend,
  fetchUserMonthlyTrend,
  fetchUserWeekdayHourHeatmap,
  fetchUserCalendarYear,
  fetchUserAvailableYears,
  fetchGuildCalendarYear,
  fetchGuildPerUserDailyMaxHours,
} from "@/lib/stats";

type Params = { userId: string };

export default async function UserPage({ params, searchParams }: { params: Params; searchParams?: { [key: string]: string | string[] | undefined } }) {
  const userId = params.userId;
  const guildIdFromEnv = process.env.DEFAULT_GUILD_ID || process.env.DEV_GUILD_ID || "";
  const hasGuild = Boolean(guildIdFromEnv);
  const guildId = hasGuild ? BigInt(guildIdFromEnv) : 0n;
  const userIdBig = BigInt(userId);

  const [detail, logs, trend, monthly, heat, years] = await Promise.all([
    fetchUserDetail(guildId, userIdBig),
    fetchUserEntryLogs(guildId, userIdBig, 100),
    fetchUserDailyTrend(guildId, userIdBig, 30),
    fetchUserMonthlyTrend(guildId, userIdBig, 12),
    fetchUserWeekdayHourHeatmap(guildId, userIdBig, 90),
    fetchUserAvailableYears(guildId, userIdBig),
  ]);

  // Year param
  const currentYear = new Date().getFullYear();
  const parsedYear = Number((searchParams?.year as string) || currentYear);
  const calendarYear = Number.isFinite(parsedYear) && parsedYear >= 2000 && parsedYear <= 3000 ? parsedYear : currentYear;
  const availYears = (years as number[]).length > 0 ? (years as number[]) : [currentYear];
  // Show only current year and any future years that exist (e.g., 2026 when the year changes)
  const yearsToShow = Array.from(new Set([currentYear, ...availYears.filter((y) => y >= currentYear)])).sort((a, b) => a - b);
  const [calendarDataRes, guildCalendar, guildPerUserDailyMaxHours] = await Promise.all([
    fetchUserCalendarYear(guildId, userIdBig, calendarYear),
    fetchGuildCalendarYear(guildId, calendarYear),
    fetchGuildPerUserDailyMaxHours(guildId, calendarYear),
  ]);
  // 상한: 길드 전체의 "개인-하루 총합" 최대값의 85%
  const base = Number(guildPerUserDailyMaxHours || 0);
  const capHours = Math.max(1, Math.round((base * 0.85) * 100) / 100);

  return (
    <main>
      <div className="panel" style={{ marginBottom: 16, display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <div>
          <div className="title">사용자 상세</div>
          <div className="subtle">최근 활동, 출입기록, 시간대 패턴</div>
        </div>
        <a href="/" aria-label="목록으로" title="목록으로" style={{ display: "inline-flex", alignItems: "center", justifyContent: "center", width: 36, height: 36, border: "1px solid var(--border)", borderRadius: 8, textDecoration: "none", color: "var(--text)" }}>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" width="20" height="20" aria-hidden="true">
            <path d="M3 9.5l9-7 9 7"/>
            <path d="M9 22V12h6v10"/>
            <path d="M21 10v10a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V10"/>
          </svg>
        </a>
      </div>

      <div className="panel" style={{ marginBottom: 16 }}>
        <div className="title" style={{ marginBottom: 8 }}>{detail?.nickname ?? "(닉네임 없음)"}</div>
        <div className="subtle">UserID: {detail?.user_id} · 학번: {detail?.student_no ?? "-"} · 레벨: {detail?.level_name ?? "-"} · 총시간: {secondsToHours(detail?.total_seconds || 0)} · 최근접속: {detail?.last_seen_at ?? "-"}</div>
      </div>

      <div className="panel" style={{ marginBottom: 16 }}>
        <div className="title" style={{ marginBottom: 8 }}>월별 활동 추이</div>
        <LineChart
          labels={(monthly ?? []).map((t: any) => String(t.month).slice(5))}
          series={[{ label: "Hours", data: (monthly ?? []).map((t: any) => Number(t.hours)), color: "#3b82f6" }]}
        />
      </div>

      <div className="panel" style={{ marginBottom: 16 }}>
        <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", marginBottom: 8 }}>
          <div className="title" style={{ marginTop: 2 }}>연간 잔디</div>
          <div style={{ display: "grid", gridTemplateRows: "repeat(auto-fit, minmax(0, 1fr))", rowGap: 6 }}>
            {yearsToShow.map((y) => (
              <a key={y} href={`?year=${y}`} className="subtle" style={{ textDecoration: "none", color: "var(--accent)", fontWeight: y === calendarYear ? 700 as any : 400 }}>{y}년</a>
            ))}
          </div>
        </div>
        <ContributionCalendar year={calendarYear} days={calendarDataRes as any} capHours={capHours} />
      </div>

      <div className="panel" style={{ marginBottom: 16 }}>
        <div className="title" style={{ marginBottom: 8 }}>요일·시간대 시각화 (최근 90일)</div>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
          <div>
            <div className="subtle" style={{ marginBottom: 8 }}>원형 시계형 히트맵</div>
            <CircularHeatmap
              labels={clockLabels()}
              data={hourSecondsFromHeat(heat as any).map((s) => Math.round((s / 3600) * 100) / 100)}
              centerText={`${formatPeak(hourSecondsFromHeat(heat as any))}`}
            />
          </div>
          <div>
            <div className="subtle" style={{ marginBottom: 8 }}>에너지 커브(%)</div>
            <EnergyCurve
              labels={clockLabels()}
              data={hourSecondsFromHeat(heat as any)}
              label="시간 분포(%)"
            />
          </div>
        </div>
      </div>

      <div className="panel" style={{ marginBottom: 16 }}>
        <div className="title" style={{ marginBottom: 8 }}>출입기록</div>
        <div style={{ overflowX: "auto" }}>
          <table>
            <thead>
              <tr>
                <th>시작</th>
                <th>종료</th>
                <th>소요</th>
              </tr>
            </thead>
            <tbody>
              {(logs ?? []).map((r: any, i: number) => (
                <tr key={i}>
                  <td style={tdMono}>{r.started_at}</td>
                  <td style={tdMono}>{r.ended_at}</td>
                  <td style={tdMono}>{secondsToHours(Number(r.duration_seconds || 0))}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </main>
  );
}

function secondsToHours(sec: number) {
  const hours = Math.floor((sec || 0) / 3600);
  const mins = Math.round(((sec || 0) % 3600) / 60);
  return `${hours}h ${mins}m`;
}

function hourIntensityFromHeat(heat: any[]): number[] {
  const arr = new Array(24).fill(0);
  for (const c of heat || []) {
    const h = Number(c.hour ?? 0);
    const v = Number(c.count ?? 0);
    if (h >= 0 && h < 24) arr[h] += v;
  }
  return arr;
}

function sumHours(heat: any[]): number {
  const total = (heat || []).reduce((acc, c) => acc + Number(c.count ?? 0), 0);
  return total;
}

function hourSecondsFromHeat(heat: any[]): number[] {
  const arr = new Array(24).fill(0);
  for (const c of heat || []) {
    const h = Number(c.hour ?? 0);
    const s = Number(c.seconds ?? 0);
    if (h >= 0 && h < 24) arr[h] += s;
  }
  return arr;
}

function clockLabels(): string[] {
  return ["12", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13", "14", "15", "16", "17", "18", "19", "20", "21", "22", "23"];
}

function formatPeak(arr: number[]): string {
  if (!arr || arr.length === 0) return "-";
  let idx = 0;
  let max = -1;
  arr.forEach((v, i) => { if (v > max) { max = v; idx = i; } });
  const hour = idx % 24;
  const label = `${hour.toString().padStart(2, '0')}:00`;
  return label;
}

const tdMono: React.CSSProperties = {
  borderBottom: "1px solid var(--border)",
  padding: "8px 6px",
  fontFamily: "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace",
  whiteSpace: "nowrap",
};


