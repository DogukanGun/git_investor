import { useQuery } from "@tanstack/react-query";
import { fetchLanguages } from "../api";

export interface FilterState {
  min_stars: number;
  max_stars: number;
  language: string;
  topic: string;
  company_only: boolean;
  funded_only: boolean;
  q: string;
}

interface Props {
  value: FilterState;
  onChange: (next: FilterState) => void;
}

const inputCls =
  "bg-void border border-line rounded-lg px-3 py-2 text-sm font-mono text-ink placeholder:text-faint focus:outline-none focus:border-signal/50 focus:ring-1 focus:ring-signal/30 transition-colors";

export default function Filters({ value, onChange }: Props) {
  const { data: languages = [] } = useQuery({ queryKey: ["languages"], queryFn: fetchLanguages });
  const set = (patch: Partial<FilterState>) => onChange({ ...value, ...patch });

  return (
    <div className="panel p-5 mb-6">
      <div className="flex flex-wrap gap-5 items-end">
        <div>
          <label className="label block mb-1.5">Star band</label>
          <div className="flex items-center gap-2">
            <input
              type="number"
              value={value.min_stars}
              min={0}
              onChange={(e) => set({ min_stars: Number(e.target.value) })}
              className={`${inputCls} w-24`}
            />
            <span className="text-faint font-mono">··</span>
            <input
              type="number"
              value={value.max_stars}
              min={0}
              onChange={(e) => set({ max_stars: Number(e.target.value) })}
              className={`${inputCls} w-24`}
            />
          </div>
        </div>

        <div>
          <label className="label block mb-1.5">Language</label>
          <select
            value={value.language}
            onChange={(e) => set({ language: e.target.value })}
            className={`${inputCls} min-w-[130px]`}
          >
            <option value="">all</option>
            {languages.map((l) => (
              <option key={l} value={l}>
                {l}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="label block mb-1.5">Topic</label>
          <input
            type="text"
            value={value.topic}
            placeholder="llm, infra…"
            onChange={(e) => set({ topic: e.target.value })}
            className={`${inputCls} w-32`}
          />
        </div>

        <div className="flex-1 min-w-[180px]">
          <label className="label block mb-1.5">Search</label>
          <input
            type="text"
            value={value.q}
            placeholder="name / description"
            onChange={(e) => set({ q: e.target.value })}
            className={`${inputCls} w-full`}
          />
        </div>

        <div className="flex items-center gap-2 pb-1">
          <Toggle
            on={value.company_only}
            onClick={() => set({ company_only: !value.company_only })}
            label="company"
            color="cyan"
          />
          <Toggle
            on={value.funded_only}
            onClick={() => set({ funded_only: !value.funded_only })}
            label="funded"
            color="amber"
          />
        </div>
      </div>
    </div>
  );
}

function Toggle({
  on,
  onClick,
  label,
  color,
}: {
  on: boolean;
  onClick: () => void;
  label: string;
  color: "cyan" | "amber";
}) {
  const active =
    color === "cyan"
      ? "border-cyan/50 text-cyan bg-cyan/10"
      : "border-amber/50 text-amber bg-amber/10";
  return (
    <button
      onClick={onClick}
      className={`font-mono text-xs uppercase tracking-wider px-3 py-2 rounded-lg border transition-colors ${
        on ? active : "border-line text-muted hover:text-ink hover:border-line-bright"
      }`}
    >
      {on ? "◉" : "○"} {label}
    </button>
  );
}
