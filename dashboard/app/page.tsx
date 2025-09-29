import { fetchGuildUserStats } from "@/lib/stats";
import { fetchSummaryToday, fetchDailyTrend, fetchLeaderboard, fetchLevelDistribution, fetchSessionLengthHistogram } from "@/lib/analytics";
import LineChart from "@/components/LineChart";
import BarChart from "@/components/BarChart";

type SearchParams = {
  q?: string;
};

export const dynamic = "force-dynamic";

export default async function Page({ searchParams }: { searchParams: SearchParams }) {
  const guildIdFromEnv = process.env.DEFAULT_GUILD_ID || process.env.DEV_GUILD_ID || "";
  const limit = 500;
  const q = searchParams.q || "";

  const hasGuild = Boolean(guildIdFromEnv);
  const guildId = hasGuild ? BigInt(guildIdFromEnv) : 0n;
  const rows = hasGuild ? await fetchGuildUserStats(guildId, limit, q) : [];
  const summary = hasGuild ? await fetchSummaryToday(guildId) : { todayHours: 0, dau: 0, avgHoursPerActive: 0 };
  const trend = hasGuild ? await fetchDailyTrend(guildId, 30) : [];
  const leadersWeek = hasGuild ? await fetchLeaderboard(guildId, "week") : [];
  const leadersMonth = hasGuild ? await fetchLeaderboard(guildId, "month") : [];
  const levelDist = hasGuild ? await fetchLevelDistribution(guildId) : [];
  const sessionHist = hasGuild ? await fetchSessionLengthHistogram(guildId, 30) : [];

  return (
    <main>
      <div className="panel" style={{ marginBottom: 16 }}>
        <div className="title">유저 통계 대시보드</div>
      </div>
      <form method="get" style={{ display: "flex", gap: 12, marginBottom: 24 }}>
        <input
          type="text"
          name="q"
          placeholder="닉네임 / 학번 / UserID 포함 검색"
          defaultValue={q}
          style={{ padding: 8, width: 380 }}
        />
        <button type="submit" style={{ padding: "8px 12px" }}>검색</button>
      </form>

      {!hasGuild ? (
        <div className="panel">좌측 폼에 Guild ID를 입력하고 조회를 눌러주세요.</div>
      ) : rows.length === 0 ? (
        <div className="panel">데이터가 없습니다.</div>
      ) : (
        <div className="panel" style={{ overflowX: "auto" }}>
          <table style={{ borderCollapse: "collapse", width: "100%" }}>
            <thead>
              <tr>
                <th style={th}>User ID</th>
                <th style={th}>Nickname</th>
                <th style={th}>Student No</th>
                <th style={th}>XP</th>
                <th style={th}>Total(h)</th>
                <th style={th}>Today(h)</th>
                <th style={th}>Week(h)</th>
                <th style={th}>Month(h)</th>
                <th style={th}>Last Seen</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={String(r.user_id)}>
                  <td style={tdMono}>{String(r.user_id)}</td>
                  <td style={td}>{r.nickname ?? ""}</td>
                  <td style={tdMono}>{r.student_no ?? ""}</td>
                  <td style={tdMono}>{r.xp}</td>
                  <td style={tdMono}>{secondsToHours(r.total_seconds)}</td>
                  <td style={tdMono}>{secondsToHours(r.today_seconds)}</td>
                  <td style={tdMono}>{secondsToHours(r.week_seconds)}</td>
                  <td style={tdMono}>{secondsToHours(r.month_seconds)}</td>
                  <td style={td}>{r.last_seen_at ?? ""}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {hasGuild && (
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


