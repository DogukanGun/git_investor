import { useState } from "react";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { fetchRepos, type Repo } from "../api";
import Filters, { type FilterState } from "../components/Filters";
import RepoTable from "../components/RepoTable";
import { fmtVelocity } from "../format";

const PAGE_SIZE = 25;

const DEFAULT_FILTERS: FilterState = {
  min_stars: 100,
  max_stars: 15000,
  language: "",
  topic: "",
  company_only: false,
  funded_only: false,
  hot_only: false,
  q: "",
};

export default function Dashboard() {
  const [filters, setFilters] = useState<FilterState>(DEFAULT_FILTERS);
  const [sort, setSort] = useState("score");
  const [order, setOrder] = useState("desc");
  const [page, setPage] = useState(1);

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["repos", filters, sort, order, page],
    queryFn: () => fetchRepos({ ...filters, sort, order, page, page_size: PAGE_SIZE }),
    placeholderData: keepPreviousData,
  });

  function onSort(col: string) {
    if (sort === col) setOrder(order === "desc" ? "asc" : "desc");
    else {
      setSort(col);
      setOrder("desc");
    }
    setPage(1);
  }

  function onFilterChange(next: FilterState) {
    setFilters(next);
    setPage(1);
  }

  const items = data?.items ?? [];
  const total = data?.total ?? 0;
  const pageCount = Math.max(1, Math.ceil(total / PAGE_SIZE));

  const topMover = items.reduce<Repo | null>(
    (best, r) => (!best || r.star_velocity > best.star_velocity ? r : best),
    null
  );
  const funded = items.filter((r) => !!r.funding_total);
  const hotCount = items.filter((r) => r.is_hot).length;

  return (
    <div>
      <div className="mb-7">
        <p className="label mb-2">// scouting rising repos before the market notices</p>
        <h1 className="font-display font-extrabold text-4xl md:text-5xl tracking-tight leading-none">
          The Radar
        </h1>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-6">
        <Kpi label="Repos tracked" value={total.toLocaleString()} accent="ink" />
        <Kpi
          label="Top mover (this page)"
          value={topMover ? `▲${fmtVelocity(topMover.star_velocity)}/d` : "—"}
          sub={topMover?.name}
          accent="signal"
        />
        <Kpi
          label="Hot this week"
          value={`${hotCount}`}
          sub="7-day rate spiking"
          accent="amber"
        />
        <Kpi
          label="Funded on page"
          value={`${funded.length}`}
          sub="venture-backed"
          accent="cyan"
        />
      </div>

      <Filters value={filters} onChange={onFilterChange} />

      {isError && (
        <div className="font-mono text-sm text-rose mb-4">⚠ {(error as Error).message}</div>
      )}

      <div className="flex items-center justify-between mb-3">
        <span className="label">
          {isLoading ? "scanning…" : `${total.toLocaleString()} signals`}
        </span>
        <span className="label">
          page {String(page).padStart(2, "0")} / {String(pageCount).padStart(2, "0")}
        </span>
      </div>

      <RepoTable
        repos={items}
        sort={sort}
        order={order}
        onSort={onSort}
        startRank={(page - 1) * PAGE_SIZE}
      />

      <div className="flex justify-center gap-3 mt-6">
        <PageBtn disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
          ← prev
        </PageBtn>
        <PageBtn disabled={page >= pageCount} onClick={() => setPage((p) => p + 1)}>
          next →
        </PageBtn>
      </div>
    </div>
  );
}

function Kpi({
  label,
  value,
  sub,
  accent,
}: {
  label: string;
  value: string;
  sub?: string;
  accent: "ink" | "signal" | "amber" | "cyan";
}) {
  const color = {
    ink: "text-ink",
    signal: "text-signal",
    amber: "text-amber",
    cyan: "text-cyan",
  }[accent];
  return (
    <div className="panel p-4 relative overflow-hidden">
      <div className="label mb-2">{label}</div>
      <div className={`font-mono font-bold text-2xl tabular-nums ${color}`}>{value}</div>
      {sub && <div className="text-muted text-xs mt-1 truncate font-body">{sub}</div>}
    </div>
  );
}

function PageBtn({
  children,
  disabled,
  onClick,
}: {
  children: React.ReactNode;
  disabled: boolean;
  onClick: () => void;
}) {
  return (
    <button
      disabled={disabled}
      onClick={onClick}
      className="font-mono text-xs uppercase tracking-wider px-5 py-2.5 rounded-lg border border-line text-muted hover:text-signal hover:border-signal/40 transition-colors disabled:opacity-30 disabled:hover:text-muted disabled:hover:border-line"
    >
      {children}
    </button>
  );
}
