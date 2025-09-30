import { fetchGuildUserStatsPaged } from "@/lib/stats";
import type { GuildUserRow, SortKey, SortOrder } from "@/lib/stats";

type SearchParams = {
  q?: string;
  page?: string;
  sort?: SortKey;
  order?: SortOrder;
};

export const dynamic = "force-dynamic";

export default async function Page({ searchParams }: { searchParams: SearchParams }) {
  const guildIdFromEnv = process.env.DEFAULT_GUILD_ID || process.env.DEV_GUILD_ID || "";
  const databaseUrl = process.env.DATABASE_URL || "";
  if (process.env.NEXT_BUILD_PHASE) {
    console.log(`[dashboard] NEXT_BUILD_PHASE=${process.env.NEXT_BUILD_PHASE}`);
  }
  if (process.env.NEXT_PHASE) {
    console.log(`[dashboard] NEXT_PHASE=${process.env.NEXT_PHASE}`);
  }
  const isBuildPhase = process.env.NEXT_BUILD_PHASE === "1" || process.env.NEXT_PHASE === "phase-production-build";
  const skipByEnv = process.env.SKIP_DASHBOARD_FETCH === "1";
  const limit = 20;
  const q = searchParams.q || "";
  const page = Math.max(Number(searchParams.page ?? 1), 1);
  const sort = (searchParams.sort as SortKey) || ("xp" as SortKey);
  const order = (searchParams.order as SortOrder) || ("desc" as SortOrder);

  const hasDb = Boolean(databaseUrl);
  const hasGuild = Boolean(guildIdFromEnv);
  const guildId = hasGuild ? BigInt(guildIdFromEnv) : 0n;
  let errorMessage: string | null = null;

  let rows: GuildUserRow[] = [];
  let total = 0;

  if (!hasDb) {
    errorMessage = "환경 변수 DATABASE_URL이 설정되지 않아 데이터를 불러올 수 없습니다.";
  }

  if (!errorMessage && skipByEnv) {
    errorMessage = "데이터 페치가 비활성화되어 있습니다. 환경 변수 SKIP_DASHBOARD_FETCH=0 으로 변경하세요.";
  }

  if (!errorMessage && !skipByEnv && !isBuildPhase && hasGuild) {
    try {
      const res = await fetchGuildUserStatsPaged(guildId, { page, limit, sort, order, query: q });
      rows = res.rows;
      total = res.total;
    } catch (error) {
      console.error("Failed to load users:", error);
      errorMessage = "데이터를 불러오는 중 오류가 발생했습니다. 환경 변수와 DB 연결을 확인해주세요.";
    }
  }

  return (
    <main>
      <div className="panel" style={{ marginBottom: 16 }}>
        <div className="title">마법사관학교 학생 목록</div>
      </div>
      <form
        method="get"
        style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 24 }}
      >
        <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
          <input
            type="text"
            name="q"
            placeholder="닉네임 / 학번 / UserID 포함 검색"
            defaultValue={q}
            style={{ padding: 8, width: 380 }}
          />
          <input type="hidden" name="page" value="1" />
          <input type="hidden" name="sort" value={sort} />
          <input type="hidden" name="order" value={order} />
          <button type="submit" style={{ padding: "8px 12px" }}>검색</button>
        </div>
        <a
          href="/stats"
          style={{ padding: "10px 14px", border: "1px solid #1f2937", borderRadius: 8, textDecoration: "none" }}
        >
          통계보기
        </a>
      </form>

      {errorMessage ? (
        <div className="panel">{errorMessage}</div>
      ) : !hasGuild ? (
        <div className="panel">좌측 폼에 Guild ID를 입력하고 조회를 눌러주세요.</div>
      ) : rows.length === 0 ? (
        <div className="panel">데이터가 없습니다.</div>
      ) : (
        <div className="panel" style={{ overflowX: "auto" }}>
          <table style={{ borderCollapse: "collapse", width: "100%" }}>
            <thead>
              <tr>
                {SortableTh({ keyName: "user_id", label: "User ID", currentSort: sort, currentOrder: order, q })}
                {SortableTh({ keyName: "nickname", label: "Nickname", currentSort: sort, currentOrder: order, q })}
                {SortableTh({ keyName: "student_no", label: "Student No", currentSort: sort, currentOrder: order, q })}
                {SortableTh({ keyName: "xp", label: "XP", currentSort: sort, currentOrder: order, q })}
                {SortableTh({ keyName: "total_seconds", label: "Total(h)", currentSort: sort, currentOrder: order, q })}
                {SortableTh({ keyName: "today_seconds", label: "Today(h)", currentSort: sort, currentOrder: order, q })}
                {SortableTh({ keyName: "week_seconds", label: "Week(h)", currentSort: sort, currentOrder: order, q })}
                {SortableTh({ keyName: "month_seconds", label: "Month(h)", currentSort: sort, currentOrder: order, q })}
                {SortableTh({ keyName: "last_seen_at", label: "Last Seen", currentSort: sort, currentOrder: order, q })}
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
          <Pagination total={total} page={page} limit={limit} q={q} sort={sort} order={order} />
        </div>
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

type SortableThProps = { keyName: SortKey; label: string; currentSort: SortKey; currentOrder: SortOrder; q: string };

function SortableTh({ keyName, label, currentSort, currentOrder, q }: SortableThProps) {
  const isActive = keyName === currentSort;
  const state: "none" | "asc" | "desc" = !isActive ? "none" : currentOrder === "asc" ? "asc" : "desc";
  const nextOrder: "asc" | "desc" = state === "asc" ? "desc" : "asc"; // none/desc -> asc, asc -> desc
  const href = `?q=${encodeURIComponent(q || "")}&page=1&sort=${keyName}&order=${nextOrder}`;
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

function Pagination({ total, page, limit, q, sort, order }: { total: number; page: number; limit: number; q: string; sort: SortKey; order: SortOrder }) {
  const pages = Math.max(Math.ceil((total || 0) / limit), 1);
  const clamp = (n: number) => Math.min(Math.max(n, 1), pages);
  const mk = (p: number) => `?q=${encodeURIComponent(q || "")}&page=${clamp(p)}&sort=${sort}&order=${order}`;
  if (pages <= 1) return null;
  const numbers = Array.from({ length: pages }, (_, i) => i + 1).slice(0, 50);
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 16, justifyContent: "center", padding: 16 }}>
      <a href={mk(page - 1)} style={pageBtn}>{"<"}</a>
      {numbers.map((n) => (
        <a key={n} href={mk(n)} style={{ ...pageNum, ...(n === page ? pageNumActive : {}) }}>{n}</a>
      ))}
      <a href={mk(page + 1)} style={pageBtn}>{">"}</a>
    </div>
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


