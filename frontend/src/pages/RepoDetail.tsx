import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { addWatch, fetchHistory, fetchRepo, fetchWatchlist, removeWatch } from "../api";
import { ageFromNow, fmtMoney, fmtNum, fmtVelocity, scoreColor } from "../format";

export default function RepoDetail() {
  const { id } = useParams();
  const repoId = Number(id);

  const { data: repo, isLoading } = useQuery({
    queryKey: ["repo", repoId],
    queryFn: () => fetchRepo(repoId),
  });
  const { data: history = [] } = useQuery({
    queryKey: ["history", repoId],
    queryFn: () => fetchHistory(repoId),
  });
  const { data: watchlist = [], refetch: refetchWatch } = useQuery({
    queryKey: ["watchlist"],
    queryFn: fetchWatchlist,
  });

  const [watched, setWatched] = useState(false);
  useEffect(() => {
    setWatched(watchlist.some((r) => r.id === repoId));
  }, [watchlist, repoId]);

  async function toggleWatch() {
    if (watched) await removeWatch(repoId);
    else await addWatch(repoId);
    setWatched(!watched);
    refetchWatch();
  }

  if (isLoading || !repo)
    return <div className="font-mono text-muted text-sm animate-pulse">loading signal…</div>;

  const chartData = history.map((s) => ({
    date: s.captured_at.slice(0, 10),
    stars: s.stars,
  }));

  return (
    <div className="animate-rise">
      <Link to="/" className="label hover:text-signal transition-colors">
        ← back to radar
      </Link>

      <div className="flex flex-wrap items-start justify-between gap-4 mt-4 pb-7 border-b border-line">
        <div className="min-w-0">
          <p className="label mb-2">{repo.owner_login}</p>
          <h1 className="font-display font-extrabold text-3xl md:text-4xl tracking-tight text-ink break-words">
            {repo.name}
          </h1>
          {repo.description && (
            <p className="text-muted mt-3 max-w-2xl leading-relaxed">{repo.description}</p>
          )}
          <div className="flex items-center gap-2 mt-4">
            {repo.is_company_backed && (
              <span className="chip border-cyan/30 text-cyan bg-cyan/5">company-backed</span>
            )}
            {!!repo.funding_total && (
              <span className="chip border-amber/30 text-amber bg-amber/5">
                {fmtMoney(repo.funding_total)} raised
              </span>
            )}
            {repo.language && (
              <span className="chip border-line text-muted">{repo.language}</span>
            )}
          </div>
        </div>

        <div className="flex items-center gap-4">
          <div className="text-right">
            <div className="label mb-1">Signal</div>
            <div className={`font-mono font-extrabold text-5xl tabular-nums ${scoreColor(repo.score)}`}>
              {(repo.score * 100).toFixed(0)}
            </div>
          </div>
          <button
            onClick={toggleWatch}
            className={`font-mono text-xs uppercase tracking-wider px-4 py-2.5 rounded-lg border transition-colors ${
              watched
                ? "border-signal/50 text-signal bg-signal/10"
                : "border-line text-muted hover:text-ink hover:border-line-bright"
            }`}
          >
            {watched ? "★ watching" : "☆ watch"}
          </button>
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-6">
        <Stat label="Stars" value={fmtNum(repo.stars)} />
        <Stat label="★ / day" value={`▲ ${fmtVelocity(repo.star_velocity)}`} accent="signal" />
        <Stat label="Contributors" value={fmtNum(repo.contributors)} />
        <Stat label="Forks" value={fmtNum(repo.forks)} />
        <Stat label="Age" value={ageFromNow(repo.created_at)} />
        <Stat label="Language" value={repo.language ?? "—"} />
        <Stat
          label="Funding raised"
          value={fmtMoney(repo.funding_total)}
          accent={repo.funding_total ? "amber" : undefined}
        />
        <Stat label="Owner type" value={repo.owner_type === "Organization" ? "Org" : "User"} />
      </div>

      <div className="grid lg:grid-cols-3 gap-5 mt-5">
        <div className="panel p-5 lg:col-span-2">
          <h2 className="label mb-4">Star trajectory</h2>
          {chartData.length < 2 ? (
            <p className="text-muted text-sm font-body py-12 text-center">
              Not enough snapshots yet — the trajectory builds as scans run over multiple days.
            </p>
          ) : (
            <ResponsiveContainer width="100%" height={260}>
              <AreaChart data={chartData} margin={{ left: -10, right: 8, top: 8 }}>
                <defs>
                  <linearGradient id="g" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#caff47" stopOpacity={0.35} />
                    <stop offset="100%" stopColor="#caff47" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="2 4" stroke="#233037" vertical={false} />
                <XAxis dataKey="date" stroke="#4d5a54" fontSize={11} tickLine={false} axisLine={false} />
                <YAxis stroke="#4d5a54" fontSize={11} tickLine={false} axisLine={false} width={48} />
                <Tooltip
                  contentStyle={{
                    background: "#0f1517",
                    border: "1px solid #233037",
                    borderRadius: 8,
                    fontFamily: "JetBrains Mono, monospace",
                    fontSize: 12,
                  }}
                  labelStyle={{ color: "#7e8e88" }}
                  itemStyle={{ color: "#caff47" }}
                />
                <Area
                  type="monotone"
                  dataKey="stars"
                  stroke="#caff47"
                  strokeWidth={2}
                  fill="url(#g)"
                />
              </AreaChart>
            </ResponsiveContainer>
          )}
        </div>

        <div className="panel p-5">
          <h2 className="label mb-4">Company / Org</h2>
          {repo.org ? (
            <div className="space-y-2 text-sm">
              <div className="font-display font-bold text-lg text-ink">
                {repo.org.name ?? repo.org.login}
              </div>
              {repo.org.location && <div className="text-muted">◷ {repo.org.location}</div>}
              {repo.org.website && (
                <a
                  href={normalizeUrl(repo.org.website)}
                  target="_blank"
                  rel="noreferrer"
                  className="text-cyan hover:underline block font-mono text-xs break-all"
                >
                  {repo.org.website}
                </a>
              )}

              {repo.org.funding_total ? (
                <div className="pt-3 mt-3 border-t border-line">
                  <div className="label mb-1">Funding (SEC Form D)</div>
                  <div className="font-mono font-bold text-2xl text-amber tabular-nums">
                    {fmtMoney(repo.org.funding_total)}
                  </div>
                  {repo.org.last_funding_at && (
                    <div className="text-muted text-xs mt-1">
                      last filing · {repo.org.last_funding_at.slice(0, 10)}
                    </div>
                  )}
                  {repo.org.funding_url && (
                    <a
                      href={repo.org.funding_url}
                      target="_blank"
                      rel="noreferrer"
                      className="text-cyan hover:underline font-mono text-xs mt-2 inline-block"
                    >
                      view filing ↗
                    </a>
                  )}
                </div>
              ) : (
                <div className="pt-3 mt-3 border-t border-line text-xs text-faint font-body">
                  No SEC funding filing matched (US issuers only).
                </div>
              )}
            </div>
          ) : (
            <p className="text-faint text-xs font-body">Personal / non-org repository.</p>
          )}

          <a
            href={repo.html_url}
            target="_blank"
            rel="noreferrer"
            className="mt-5 block text-center font-mono text-xs uppercase tracking-wider px-4 py-2.5 rounded-lg border border-line text-muted hover:text-signal hover:border-signal/40 transition-colors"
          >
            open on github ↗
          </a>
        </div>
      </div>
    </div>
  );
}

function Stat({
  label,
  value,
  accent,
}: {
  label: string;
  value: string;
  accent?: "signal" | "amber";
}) {
  const color = accent === "signal" ? "text-signal" : accent === "amber" ? "text-amber" : "text-ink";
  return (
    <div className="panel p-4">
      <div className="label mb-1.5">{label}</div>
      <div className={`font-mono font-bold text-xl tabular-nums ${color}`}>{value}</div>
    </div>
  );
}

function normalizeUrl(url: string): string {
  return /^https?:\/\//.test(url) ? url : `https://${url}`;
}
