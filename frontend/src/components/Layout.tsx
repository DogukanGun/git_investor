import { useState } from "react";
import { Link, Outlet, useLocation } from "react-router-dom";
import { triggerRefresh } from "../api";

export default function Layout() {
  const { pathname } = useLocation();
  const [refreshMsg, setRefreshMsg] = useState<string | null>(null);
  const [scanning, setScanning] = useState(false);

  async function onRefresh() {
    setScanning(true);
    setRefreshMsg("initiating scan…");
    const r = await triggerRefresh();
    setRefreshMsg(
      r.status === "started"
        ? "scan running — new signals incoming"
        : r.status === "already_running"
          ? "scan already in progress"
          : r.status
    );
    setTimeout(() => {
      setRefreshMsg(null);
      setScanning(false);
    }, 6000);
  }

  const tab = (to: string, label: string) => {
    const active = pathname === to;
    return (
      <Link
        to={to}
        className={`relative px-3 py-1.5 font-mono text-xs uppercase tracking-wider transition-colors ${
          active ? "text-signal" : "text-muted hover:text-ink"
        }`}
      >
        {label}
        {active && <span className="absolute -bottom-px left-3 right-3 h-px bg-signal" />}
      </Link>
    );
  };

  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-30 border-b border-line bg-void/80 backdrop-blur-md">
        <div className="max-w-[1320px] mx-auto px-6 h-16 flex items-center gap-6">
          <Link to="/" className="flex items-center gap-3 group">
            <span className="relative flex h-2.5 w-2.5">
              <span className="absolute inline-flex h-full w-full rounded-full bg-signal animate-blip" />
              <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-signal" />
            </span>
            <span className="font-display font-extrabold text-xl tracking-tight text-ink">
              git<span className="text-signal">invest</span>
            </span>
          </Link>

          <span className="label hidden md:inline border-l border-line pl-6">
            open-source alpha terminal
          </span>

          <nav className="flex items-center gap-1 ml-2">
            {tab("/", "Radar")}
            {tab("/watchlist", "Watchlist")}
          </nav>

          <div className="ml-auto flex items-center gap-4">
            {refreshMsg && (
              <span className="font-mono text-[11px] text-cyan hidden sm:inline animate-rise">
                {refreshMsg}
              </span>
            )}
            <button
              onClick={onRefresh}
              disabled={scanning}
              className="relative overflow-hidden group font-mono text-xs uppercase tracking-wider px-4 py-2 rounded-lg border border-signal/40 bg-signal/10 text-signal hover:bg-signal/20 transition-colors disabled:opacity-60"
            >
              {scanning && (
                <span className="absolute inset-y-0 w-1/3 bg-signal/20 blur-md animate-sweep" />
              )}
              <span className="relative">{scanning ? "scanning" : "▸ scan"}</span>
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-[1320px] mx-auto px-6 py-8">
        <Outlet />
      </main>

      <footer className="max-w-[1320px] mx-auto px-6 py-8 mt-8 border-t border-line">
        <p className="label">
          signals from github · funding from sec edgar form d · not investment advice
        </p>
      </footer>
    </div>
  );
}
