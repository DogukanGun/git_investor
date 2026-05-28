export interface Repo {
  id: number;
  full_name: string;
  name: string;
  owner_login: string;
  owner_type: string;
  description: string | null;
  html_url: string;
  homepage: string | null;
  language: string | null;
  topics: string | null;
  stars: number;
  forks: number;
  contributors: number | null;
  created_at: string;
  pushed_at: string | null;
  star_velocity: number;
  contributor_velocity: number;
  is_company_backed: boolean;
  funding_total: number | null;
  last_funding_at: string | null;
  score: number;
  last_updated: string;
}

export interface Org {
  login: string;
  name: string | null;
  website: string | null;
  location: string | null;
  funding_total: number | null;
  last_funding_at: string | null;
  funding_source: string | null;
  funding_url: string | null;
}

export interface RepoDetail extends Repo {
  org: Org | null;
}

export interface Snapshot {
  stars: number;
  forks: number;
  contributors: number | null;
  captured_at: string;
}

export interface RepoList {
  total: number;
  page: number;
  page_size: number;
  items: Repo[];
}

export interface RepoFilters {
  min_stars?: number;
  max_stars?: number;
  language?: string;
  topic?: string;
  company_only?: boolean;
  funded_only?: boolean;
  q?: string;
  sort?: string;
  order?: string;
  page?: number;
  page_size?: number;
}

async function getJSON<T>(url: string): Promise<T> {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json() as Promise<T>;
}

export function fetchRepos(filters: RepoFilters): Promise<RepoList> {
  const params = new URLSearchParams();
  Object.entries(filters).forEach(([k, v]) => {
    if (v !== undefined && v !== "" && v !== false) params.set(k, String(v));
  });
  return getJSON<RepoList>(`/api/repos?${params.toString()}`);
}

export const fetchRepo = (id: number) => getJSON<RepoDetail>(`/api/repos/${id}`);
export const fetchHistory = (id: number) => getJSON<Snapshot[]>(`/api/repos/${id}/history`);
export const fetchLanguages = () => getJSON<string[]>(`/api/languages`);
export const fetchWatchlist = () => getJSON<Repo[]>(`/api/watchlist`);

export async function triggerRefresh(): Promise<{ status: string }> {
  const res = await fetch(`/api/refresh`, { method: "POST" });
  return res.json();
}

export async function addWatch(id: number) {
  await fetch(`/api/watchlist/${id}`, { method: "POST" });
}

export async function removeWatch(id: number) {
  await fetch(`/api/watchlist/${id}`, { method: "DELETE" });
}
