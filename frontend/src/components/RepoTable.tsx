import { Link } from "react-router-dom";
import type { Repo } from "../api";
import { ageFromNow, fmtMoney, fmtNum, fmtVelocity, scoreColor } from "../format";

interface Props {
  repos: Repo[];
  sort: string;
  order: string;
  onSort: (col: string) => void;
  startRank?: number;
}

const COLS: { key: string; label: string; sortable: boolean; align?: string }[] = [
  { key: "rank", label: "#", sortable: false },
  { key: "full_name", label: "Repository", sortable: false },
  { key: "score", label: "Signal", sortable: true, align: "right" },
  { key: "stars", label: "Stars", sortable: true, align: "right" },
  { key: "recent_velocity", label: "★/day 30d", sortable: true, align: "right" },
  { key: "contributors", label: "Contrib", sortable: true, align: "right" },
  { key: "funding_total", label: "Raised", sortable: true, align: "right" },
  { key: "created_at", label: "Age", sortable: true, align: "right" },
];

export default function RepoTable({ repos, sort, order, onSort, startRank = 0 }: Props) {
  return (
    <div className="panel overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-sm border-collapse">
          <thead>
            <tr className="border-b border-line">
              {COLS.map((c) => (
                <th
                  key={c.key}
                  onClick={() => c.sortable && onSort(c.key)}
                  className={`px-4 py-3 label ${c.align === "right" ? "text-right" : "text-left"} ${
                    c.sortable ? "cursor-pointer hover:text-signal transition-colors" : ""
                  }`}
                >
                  {c.label}
                  {sort === c.key && <span className="ml-1 text-signal">{order === "desc" ? "↓" : "↑"}</span>}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {repos.map((r, i) => (
              <tr
                key={r.id}
                style={{ animationDelay: `${Math.min(i, 18) * 28}ms` }}
                className="group border-b border-line/60 last:border-0 hover:bg-signal/[0.03] transition-colors animate-rise"
              >
                <td className="px-4 py-3 font-mono text-xs text-faint tabular-nums">
                  {String(startRank + i + 1).padStart(2, "0")}
                </td>

                <td className="px-4 py-3 max-w-[420px]">
                  <Link
                    to={`/repo/${r.id}`}
                    className="font-medium text-ink group-hover:text-signal transition-colors"
                  >
                    {r.full_name}
                  </Link>
                  <div className="flex items-center gap-1.5 mt-1">
                    {r.is_hot && (
                      <span className="chip border-amber/40 text-amber bg-amber/10">🔥 hot</span>
                    )}
                    {r.is_company_backed && (
                      <span className="chip border-cyan/30 text-cyan bg-cyan/5">company</span>
                    )}
                    {!!r.funding_total && (
                      <span className="chip border-amber/30 text-amber bg-amber/5">
                        {fmtMoney(r.funding_total)}
                      </span>
                    )}
                    {r.description && (
                      <span className="text-muted text-xs truncate font-body">{r.description}</span>
                    )}
                  </div>
                </td>

                <td className="px-4 py-3 text-right align-middle w-[120px]">
                  <div className={`font-mono font-bold text-lg tabular-nums ${scoreColor(r.score)}`}>
                    {(r.score * 100).toFixed(0)}
                  </div>
                  <div className="mt-1 h-1 w-full rounded-full bg-line overflow-hidden">
                    <div
                      className="h-full rounded-full bg-current origin-left animate-grow"
                      style={{ width: `${Math.max(2, r.score * 100)}%` }}
                    />
                  </div>
                </td>

                <td className="px-4 py-3 text-right font-mono text-ink tabular-nums">
                  {fmtNum(r.stars)}
                </td>
                <td className="px-4 py-3 text-right font-mono text-signal tabular-nums">
                  <span className="text-signal-dim mr-0.5">▲</span>
                  {fmtVelocity(r.recent_velocity)}
                </td>
                <td className="px-4 py-3 text-right font-mono text-muted tabular-nums">
                  {fmtNum(r.contributors)}
                </td>
                <td className="px-4 py-3 text-right font-mono tabular-nums">
                  <span className={r.funding_total ? "text-amber" : "text-faint"}>
                    {fmtMoney(r.funding_total)}
                  </span>
                </td>
                <td className="px-4 py-3 text-right font-mono text-muted tabular-nums">
                  {ageFromNow(r.created_at)}
                </td>
              </tr>
            ))}
            {repos.length === 0 && (
              <tr>
                <td colSpan={COLS.length} className="px-4 py-16 text-center">
                  <div className="font-mono text-muted text-sm">no signals in range</div>
                  <div className="text-faint text-xs mt-1 font-body">
                    widen the star band or run a scan
                  </div>
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
