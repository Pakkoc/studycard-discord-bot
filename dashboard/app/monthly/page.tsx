import { fetchMonthlyRankingPaged, fetchAvailableMonths } from "@/lib/stats";
import type { MonthlyUserRow, MonthlySortKey, SortOrder } from "@/lib/stats";

type SearchParams = {
  month?: string;
  q?: string;
  page?: string;
  sort?: MonthlySortKey;
  order?: SortOrder;
};

export const dynamic = "force-dynamic";

function getCurrentMonth(): string {
  const now = new Date();
  const year = now.getFullYear();
  const month = now.getMonth() + 1;
  return `${year}-${String(month).padStart(2, "0")}`;
}

export default async function MonthlyPage({ searchParams }: { searchParams: SearchParams }) {
  const guildIdFromEnv = process.env.DEFAULT_GUILD_ID || process.env.DEV_GUILD_ID || "";
  const databaseUrl = process.env.DATABASE_URL || "";

  const isBuildPhaseEnv = process.env.NEXT_BUILD_PHASE === "1" || process.env.NEXT_PHASE === "phase-production-build";
  const isBuildPhase = process.env.NODE_ENV !== "development" && isBuildPhaseEnv;
  const skipByEnv = process.env.SKIP_DASHBOARD_FETCH === "1";

  const hasDb = Boolean(databaseUrl);
  const hasGuild = Boolean(guildIdFromEnv);
  const guildId = hasGuild ? BigInt(guildIdFromEnv) : 0n;

  const limit = 20;
  const q = searchParams.q || "";
  const page = Math.max(Number(searchParams.page ?? 1), 1);
  const sort = (searchParams.sort as MonthlySortKey) || "month_seconds";
  const order = (searchParams.order as SortOrder) || "desc";

  let errorMessage: string | null = null;
  let rows: MonthlyUserRow[] = [];
  let total = 0;
  let availableMonths: string[] = [];
  let selectedMonth = searchParams.month || getCurrentMonth();

  if (!hasDb) {
    errorMessage = "환경 변수 DATABASE_URL이 설정되지 않아 데이터를 불러올 수 없습니다.";
  }

  if (!errorMessage && skipByEnv) {
    errorMessage = "데이터 페치가 비활성화되어 있습니다.";
  }

  if (!errorMessage && !skipByEnv && !isBuildPhase && hasGuild) {
    try {
      availableMonths = await fetchAvailableMonths(guildId);
      if (availableMonths.length > 0 && !availableMonths.includes(selectedMonth)) {
        selectedMonth = availableMonths[0];
      }
      const res = await fetchMonthlyRankingPaged(guildId, selectedMonth, { page, limit, sort, order, query: q });
      rows = res.rows;
      total = res.total;
    } catch (error) {
      console.error("Failed to load monthly ranking:", error);
      errorMessage = "데이터를 불러오는 중 오류가 발생했습니다.";
    }
  }

  const [yearPart, monthPart] = selectedMonth.split("-");
  const monthLabel = `${yearPart}년 ${parseInt(monthPart, 10)}월`;

  return (
    <main>
      <div className="panel" style={{ marginBottom: 16, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div>
          <div className="title">월간 랭킹</div>
          <div className="subtle">월별 공부 시간 및 반응 랭킹</div>
        </div>
        <a
          href="/"
          style={{
            display: "inline-flex",
            alignItems: "center",
            justifyContent: "center",
            width: 36,
            height: 36,
            border: "1px solid var(--border)",
            borderRadius: 8,
            textDecoration: "none",
            color: "var(--text)",
          }}
          aria-label="목록으로"
          title="목록으로"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" width="20" height="20" aria-hidden="true">
            <path d="M3 9.5l9-7 9 7"/>
            <path d="M9 22V12h6v10"/>
            <path d="M21 10v10a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V10"/>
          </svg>
        </a>
      </div>

      <form method="get" style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 24, flexWrap: "wrap" }}>
        <select
          name="month"
          defaultValue={selectedMonth}
          style={{ padding: "8px 12px", borderRadius: 8, border: "1px solid var(--border)", background: "var(--bg)", color: "var(--text)" }}
        >
          {availableMonths.map((m) => {
            const [y, mo] = m.split("-");
            return (
              <option key={m} value={m}>
                {y}년 {parseInt(mo, 10)}월
              </option>
            );
          })}
        </select>
        <input
          type="text"
          name="q"
          placeholder="닉네임 / 학번 검색"
          defaultValue={q}
          style={{ padding: 8, width: 240 }}
        />
        <input type="hidden" name="page" value="1" />
        <input type="hidden" name="sort" value={sort} />
        <input type="hidden" name="order" value={order} />
        <button type="submit" style={{ padding: "8px 12px" }}>조회</button>
      </form>

      {errorMessage ? (
        <div className="panel">{errorMessage}</div>
      ) : !hasGuild ? (
        <div className="panel">Guild ID가 설정되지 않았습니다.</div>
      ) : rows.length === 0 ? (
        <div className="panel">{monthLabel}에 데이터가 없습니다.</div>
      ) : (
        <div className="panel" style={{ overflowX: "auto" }}>
          <div style={{ marginBottom: 12, fontSize: 18, fontWeight: 600 }}>{monthLabel} 랭킹</div>
          <table style={{ borderCollapse: "collapse", width: "100%" }}>
            <thead>
              <tr>
                <th style={th}>순위</th>
                {SortableTh({ keyName: "nickname", label: "Nickname", currentSort: sort, currentOrder: order, q, month: selectedMonth })}
                {SortableTh({ keyName: "student_no", label: "Student No", currentSort: sort, currentOrder: order, q, month: selectedMonth })}
                <th style={th}>Status</th>
                <th style={th}>Level</th>
                {SortableTh({ keyName: "month_seconds", label: "공부 시간", currentSort: sort, currentOrder: order, q, month: selectedMonth })}
                {SortableTh({ keyName: "month_reaction_count", label: "반응 수", currentSort: sort, currentOrder: order, q, month: selectedMonth })}
              </tr>
            </thead>
            <tbody>
              {rows.map((r, idx) => {
                const rank = (page - 1) * limit + idx + 1;
                return (
                  <tr key={String(r.user_id)}>
                    <td style={tdMono}>{rank}</td>
                    <td style={td}>
                      <a href={`/users/${String(r.user_id)}`} style={{ color: "var(--accent)", textDecoration: "none" }}>
                        {r.nickname ?? ""}
                      </a>
                    </td>
                    <td style={tdMono}>{r.student_no ?? ""}</td>
                    <td style={td}><StatusBadge status={r.status} /></td>
                    <td style={td}>{r.level_name ?? ""}</td>
                    <td style={tdMono}>{secondsToHours(r.month_seconds)}</td>
                    <td style={tdMono}>{r.month_reaction_count}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          <Pagination total={total} page={page} limit={limit} q={q} sort={sort} order={order} month={selectedMonth} />
        </div>
      )}
    </main>
  );
}

const th: React.CSSProperties = {
  textAlign: "left",
  borderBottom: "1px solid #e5e7eb",
  padding: "10px 12px",
  fontWeight: 600,
};

const td: React.CSSProperties = {
  borderBottom: "1px solid #f1f5f9",
  padding: "10px 12px",
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

type SortableThProps = {
  keyName: MonthlySortKey;
  label: string;
  currentSort: MonthlySortKey;
  currentOrder: SortOrder;
  q: string;
  month: string;
};

function SortableTh({ keyName, label, currentSort, currentOrder, q, month }: SortableThProps) {
  const isActive = keyName === currentSort;
  const state: "none" | "asc" | "desc" = !isActive ? "none" : currentOrder === "asc" ? "asc" : "desc";
  const nextOrder: "asc" | "desc" = state === "asc" ? "desc" : "asc";
  const href = `?month=${encodeURIComponent(month)}&q=${encodeURIComponent(q || "")}&page=1&sort=${keyName}&order=${nextOrder}`;
  const ariaSort = state === "none" ? "none" : state === "asc" ? "ascending" : "descending";
  const ariaLabel = `${label} 정렬: ${nextOrder === "asc" ? "오름차순" : "내림차순"}으로 변경`;
  return (
    <th style={th} aria-sort={ariaSort as any}>
      <a href={href} className={`sort-btn${isActive ? " sort-active" : ""}`} aria-label={ariaLabel}>
        <span>{label}</span>
        {SortIcon(state)}
      </a>
    </th>
  );
}

function SortIcon(state: "none" | "asc" | "desc") {
  const upOpacity = state === "asc" ? 1 : state === "none" ? 0.6 : 0.35;
  const downOpacity = state === "desc" ? 1 : state === "none" ? 0.6 : 0.35;
  return (
    <svg className="sort-icon" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M6 8l4-4 4 4" style={{ opacity: upOpacity }} />
      <path d="M6 14l4 4 4-4" style={{ opacity: downOpacity }} />
    </svg>
  );
}

function Pagination({
  total,
  page,
  limit,
  q,
  sort,
  order,
  month,
}: {
  total: number;
  page: number;
  limit: number;
  q: string;
  sort: MonthlySortKey;
  order: SortOrder;
  month: string;
}) {
  const pages = Math.max(Math.ceil((total || 0) / limit), 1);
  if (pages <= 1) return null;

  const clamp = (n: number) => Math.min(Math.max(n, 1), pages);
  const mk = (p: number) => `?month=${encodeURIComponent(month)}&q=${encodeURIComponent(q || "")}&page=${clamp(p)}&sort=${sort}&order=${order}`;

  const groupSize = 10;
  const currentGroup = Math.ceil(page / groupSize);
  const lastGroup = Math.ceil(pages / groupSize);
  const groupStart = (currentGroup - 1) * groupSize + 1;
  const groupEnd = Math.min(groupStart + groupSize - 1, pages);

  const pageNumbers = [] as number[];
  for (let n = groupStart; n <= groupEnd; n++) pageNumbers.push(n);

  const hasPrevGroup = currentGroup > 1;
  const hasNextGroup = currentGroup < lastGroup;
  const prevGroupPage = groupStart - groupSize;
  const nextGroupPage = groupStart + groupSize;

  return (
    <div style={{ display: "flex", alignItems: "center", gap: 16, justifyContent: "center", padding: 16 }}>
      {hasPrevGroup ? (
        <a href={mk(prevGroupPage)} style={pageBtn}>{"<"}</a>
      ) : (
        <span style={{ ...pageBtn, opacity: 0.35, pointerEvents: "none" }}>{"<"}</span>
      )}
      {pageNumbers.map((n) => (
        <a key={n} href={mk(n)} style={{ ...pageNum, ...(n === page ? pageNumActive : {}) }}>{n}</a>
      ))}
      {hasNextGroup ? (
        <a href={mk(nextGroupPage)} style={pageBtn}>{">"}</a>
      ) : (
        <span style={{ ...pageBtn, opacity: 0.35, pointerEvents: "none" }}>{">"}</span>
      )}
    </div>
  );
}

function StatusBadge({ status }: { status: "active" | "left" }) {
  const label = status === "left" ? "Left" : "Active";
  const color = status === "left" ? "#ef4444" : "#10b981";
  const bg = status === "left" ? "rgba(239, 68, 68, 0.1)" : "rgba(16, 185, 129, 0.1)";
  return (
    <span style={{ padding: "2px 8px", borderRadius: 12, fontSize: 12, color, backgroundColor: bg }}>{label}</span>
  );
}

const pageBtn: React.CSSProperties = {
  border: "1px solid #1f2937",
  padding: "6px 10px",
  borderRadius: 8,
  textDecoration: "none",
  color: "#e5e7eb",
};

const pageNum: React.CSSProperties = {
  textDecoration: "none",
  color: "#e5e7eb",
};

const pageNumActive: React.CSSProperties = {
  color: "#f59e0b",
  fontWeight: 700,
};
