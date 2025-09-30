import LineChart from "@/components/LineChart";
import BarChart from "@/components/BarChart";
import {
  fetchSummaryToday,
  fetchDailyTrend,
  fetchLeaderboard,
  fetchLevelDistribution,
  fetchSessionLengthHistogram,
} from "@/lib/analytics";
import type {
  SummaryToday,
  DailyTrendPoint,
  LeaderRow,
  LevelBucket,
  SessionBucket,
} from "@/lib/analytics";

export const dynamic = "force-dynamic";

export default async function StatsPage() {
  const guildIdFromEnv = process.env.DEFAULT_GUILD_ID || process.env.DEV_GUILD_ID || "";
  const databaseUrl = process.env.DATABASE_URL || "";
  const isBuildPhase = process.env.NEXT_BUILD_PHASE === "1" || process.env.NEXT_PHASE === "phase-production-build";
  const skipByEnv = process.env.SKIP_DASHBOARD_FETCH === "1";

  const hasDb = Boolean(databaseUrl);
  const hasGuild = Boolean(guildIdFromEnv);
  const guildId = hasGuild ? BigInt(guildIdFromEnv) : 0n;
  let errorMessage: string | null = null;

  let summary: SummaryToday = { todayHours: 0, dau: 0, avgHoursPerActive: 0 };
  let trend: DailyTrendPoint[] = [];
  let leadersWeek: LeaderRow[] = [];
  let leadersMonth: LeaderRow[] = [];
  let levelDist: LevelBucket[] = [];
  let sessionHist: SessionBucket[] = [];

  if (!hasDb) {
    errorMessage = "환경 변수 DATABASE_URL이 설정되지 않아 데이터를 불러올 수 없습니다.";
  }
  if (!errorMessage && skipByEnv) {
    errorMessage = "데이터 페치가 비활성화되어 있습니다. 환경 변수 SKIP_DASHBOARD_FETCH=0 으로 변경하세요.";
  }

  if (!errorMessage && !isBuildPhase && hasGuild) {
    try {
      [summary, trend, leadersWeek, leadersMonth, levelDist, sessionHist] = await Promise.all([
        fetchSummaryToday(guildId),
        fetchDailyTrend(guildId, 30),
        fetchLeaderboard(guildId, "week"),
        fetchLeaderboard(guildId, "month"),
        fetchLevelDistribution(guildId),
        fetchSessionLengthHistogram(guildId, 30),
      ]);
    } catch (e) {
      console.error(e);
      errorMessage = "통계를 불러오는 중 오류가 발생했습니다.";
    }
  }

  return (
    <main>
      <div className="panel" style={{ marginBottom: 16 }}>
        <div className="title">통계</div>
        <div className="subtle">유저 정보 외의 모든 통계가 이 페이지에 모였습니다.</div>
      </div>

      {errorMessage ? (
        <div className="panel">{errorMessage}</div>
      ) : !hasGuild ? (
        <div className="panel">환경 변수를 통해 Guild ID를 설정해주세요.</div>
      ) : (
        <>
          <div className="cards">
            <div className="card-kpi">
              <div className="kpi-label">오늘 총 학습시간</div>
              <div className="kpi-value">{summary.todayHours.toFixed(2)} h</div>
            </div>
            <div className="card-kpi">
              <div className="kpi-label">DAU</div>
              <div className="kpi-value">{summary.dau}</div>
            </div>
            <div className="card-kpi">
              <div className="kpi-label">1인당 평균(오늘)</div>
              <div className="kpi-value">{summary.avgHoursPerActive.toFixed(2)} h</div>
            </div>
          </div>

          <div className="panel" style={{ marginBottom: 16 }}>
            <div className="title" style={{ marginBottom: 8 }}>일간 추이 (총시간/DAU)</div>
            <LineChart
              labels={trend.map((t) => t.date.slice(5))}
              series={[
                { label: "Hours", data: trend.map((t) => t.hours), color: "#60a5fa" },
                { label: "DAU", data: trend.map((t) => t.dau), color: "#fca5a5" },
              ]}
            />
          </div>

          <div className="panel" style={{ marginBottom: 16 }}>
            <div className="title" style={{ marginBottom: 8 }}>리더보드</div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
              <div>
                <div className="subtle" style={{ marginBottom: 8 }}>이번주 TOP 20</div>
                <table>
                  <thead>
                    <tr>
                      <th style={th}>User</th>
                      <th style={th}>Week(h)</th>
                    </tr>
                  </thead>
                  <tbody>
                    {leadersWeek.map((l) => (
                      <tr key={`w-${l.user_id}`}>
                        <td style={td}>{l.nickname ?? l.user_id}</td>
                        <td style={tdMono}>{secondsToHours(l.value_seconds)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div>
                <div className="subtle" style={{ marginBottom: 8 }}>이번달 TOP 20</div>
                <table>
                  <thead>
                    <tr>
                      <th style={th}>User</th>
                      <th style={th}>Month(h)</th>
                    </tr>
                  </thead>
                  <tbody>
                    {leadersMonth.map((l) => (
                      <tr key={`m-${l.user_id}`}>
                        <td style={td}>{l.nickname ?? l.user_id}</td>
                        <td style={tdMono}>{secondsToHours(l.value_seconds)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>

          <div className="panel" style={{ marginBottom: 16 }}>
            <div className="title" style={{ marginBottom: 8 }}>분포</div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
              <div>
                <div className="subtle" style={{ marginBottom: 8 }}>레벨 분포</div>
                <BarChart labels={levelDist.map((d) => `L${d.level}`)} data={levelDist.map((d) => d.users)} />
              </div>
              <div>
                <div className="subtle" style={{ marginBottom: 8 }}>세션 길이 히스토그램(최근 30일)</div>
                <BarChart
                  labels={sessionHist.map((s) => s.bucket)}
                  data={sessionHist.map((s) => s.count)}
                  color="#34d399"
                />
              </div>
            </div>
          </div>
        </>
      )}
    </main>
  );
}

const th: React.CSSProperties = {
  textAlign: "left",
  borderBottom: "1px solid #e5e7eb",
  padding: "8px 6px",
  fontWeight: 600,
};

const td: React.CSSProperties = {
  borderBottom: "1px solid #f1f5f9",
  padding: "8px 6px",
};

const tdMono: React.CSSProperties = {
  ...td,
  fontFamily: "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace",
  whiteSpace: "nowrap",
};

function secondsToHours(sec: number) {
  const hours = Math.floor((sec || 0) / 3600);
  const mins = Math.round(((sec || 0) % 3600) / 60);
  return `${hours}h ${mins}m`;
}


