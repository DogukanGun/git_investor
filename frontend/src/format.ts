export function ageFromNow(iso: string): string {
  const days = (Date.now() - new Date(iso + "Z").getTime()) / 86400000;
  if (days < 30) return `${Math.round(days)}d`;
  if (days < 365) return `${Math.round(days / 30)}mo`;
  return `${(days / 365).toFixed(1)}y`;
}

export function fmtNum(n: number | null | undefined): string {
  if (n === null || n === undefined) return "—";
  if (n >= 1000) return `${(n / 1000).toFixed(1)}k`;
  return String(n);
}

export function fmtVelocity(v: number): string {
  if (v >= 10) return v.toFixed(0);
  return v.toFixed(1);
}

export function fmtMoney(n: number | null | undefined): string {
  if (!n || n <= 0) return "—";
  if (n >= 1_000_000_000) return `$${(n / 1_000_000_000).toFixed(1)}B`;
  if (n >= 1_000_000) return `$${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `$${(n / 1_000).toFixed(0)}K`;
  return `$${n}`;
}

export function scoreColor(score: number): string {
  if (score >= 0.6) return "text-signal";
  if (score >= 0.4) return "text-amber";
  return "text-muted";
}
