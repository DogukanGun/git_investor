import { useQuery } from "@tanstack/react-query";
import { fetchWatchlist } from "../api";
import RepoTable from "../components/RepoTable";

export default function Watchlist() {
  const { data: repos = [], isLoading } = useQuery({
    queryKey: ["watchlist"],
    queryFn: fetchWatchlist,
  });

  return (
    <div className="animate-rise">
      <div className="mb-7">
        <p className="label mb-2">// positions you're tracking</p>
        <h1 className="font-display font-extrabold text-4xl md:text-5xl tracking-tight leading-none">
          Watchlist
        </h1>
      </div>
      {isLoading ? (
        <div className="font-mono text-muted text-sm animate-pulse">loading…</div>
      ) : repos.length === 0 ? (
        <div className="panel p-16 text-center">
          <div className="font-mono text-muted text-sm">watchlist empty</div>
          <div className="text-faint text-xs mt-1 font-body">
            star repos on the radar to track them here
          </div>
        </div>
      ) : (
        <RepoTable repos={repos} sort="score" order="desc" onSort={() => {}} />
      )}
    </div>
  );
}
