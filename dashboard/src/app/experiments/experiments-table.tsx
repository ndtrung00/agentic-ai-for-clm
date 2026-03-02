"use client";

import { useState, useMemo, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import type { ExperimentListItem } from "@/lib/types";
import { pct, fixed, usd, duration, formatDate } from "@/lib/format";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { ExportButton } from "@/components/ui/export-button";
import { Pagination, paginate } from "@/components/ui/pagination";

interface ExperimentsTableProps {
  experiments: ExperimentListItem[];
}

type SortKey = keyof ExperimentListItem;

const STORAGE_KEY = "experiments-table-filters";
const HIDDEN_KEY = "experiments-table-hidden";

type RunMode = "all" | "official" | "test";

interface FilterState {
  search: string;
  configFilter: string;
  modelFilter: string;
  providerFilter: string;
  runMode: RunMode;
  sortKey: SortKey;
  sortDir: "asc" | "desc";
}

const DEFAULT_FILTERS: FilterState = {
  search: "",
  configFilter: "all",
  modelFilter: "all",
  providerFilter: "all",
  runMode: "official",
  sortKey: "timestamp",
  sortDir: "desc",
};

function loadFilters(): FilterState {
  if (typeof window === "undefined") return DEFAULT_FILTERS;
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      const parsed = JSON.parse(stored);
      return { ...DEFAULT_FILTERS, ...parsed };
    }
  } catch {
    // ignore
  }
  return DEFAULT_FILTERS;
}

function saveFilters(filters: FilterState) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(filters));
  } catch {
    // ignore
  }
}

function loadHiddenRuns(): Set<string> {
  if (typeof window === "undefined") return new Set();
  try {
    const stored = localStorage.getItem(HIDDEN_KEY);
    if (stored) return new Set(JSON.parse(stored));
  } catch {
    // ignore
  }
  return new Set();
}

function saveHiddenRuns(hidden: Set<string>) {
  try {
    localStorage.setItem(HIDDEN_KEY, JSON.stringify([...hidden]));
  } catch {
    // ignore
  }
}

export function ExperimentsTable({ experiments }: ExperimentsTableProps) {
  const router = useRouter();
  const [filters, setFilters] = useState<FilterState>(DEFAULT_FILTERS);
  const [hydrated, setHydrated] = useState(false);
  const [selectedRuns, setSelectedRuns] = useState<Set<string>>(new Set());
  const [hiddenRuns, setHiddenRuns] = useState<Set<string>>(new Set());
  const [showHidden, setShowHidden] = useState(false);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(25);

  // Load from localStorage on mount
  useEffect(() => {
    setFilters(loadFilters());
    setHiddenRuns(loadHiddenRuns());
    setHydrated(true);
  }, []);

  // Save to localStorage on change (after hydration)
  useEffect(() => {
    if (hydrated) saveFilters(filters);
  }, [filters, hydrated]);

  useEffect(() => {
    if (hydrated) saveHiddenRuns(hiddenRuns);
  }, [hiddenRuns, hydrated]);

  const updateFilter = useCallback(
    <K extends keyof FilterState>(key: K, value: FilterState[K]) => {
      setFilters((prev) => ({ ...prev, [key]: value }));
    },
    [],
  );

  // Unique values for filter dropdowns
  const configTypes = useMemo(
    () => [...new Set(experiments.map((e) => e.baseline_type))].sort(),
    [experiments],
  );

  const modelKeys = useMemo(
    () => [...new Set(experiments.map((e) => e.model_key))].sort(),
    [experiments],
  );

  const providers = useMemo(
    () => [...new Set(experiments.map((e) => e.provider))].sort(),
    [experiments],
  );

  const filtered = useMemo(() => {
    let result = [...experiments];

    // Apply hidden filter
    if (!showHidden) {
      result = result.filter((e) => !hiddenRuns.has(e.run_id));
    }

    // Apply run mode filter
    if (filters.runMode !== "all") {
      result = result.filter((e) => e.run_mode === filters.runMode);
    }

    if (filters.configFilter !== "all") {
      result = result.filter((e) => e.baseline_type === filters.configFilter);
    }

    if (filters.modelFilter !== "all") {
      result = result.filter((e) => e.model_key === filters.modelFilter);
    }

    if (filters.providerFilter !== "all") {
      result = result.filter((e) => e.provider === filters.providerFilter);
    }

    if (filters.search) {
      const q = filters.search.toLowerCase();
      result = result.filter(
        (e) =>
          e.model_key.toLowerCase().includes(q) ||
          e.provider.toLowerCase().includes(q) ||
          e.run_id.toLowerCase().includes(q),
      );
    }

    result.sort((a, b) => {
      const av = a[filters.sortKey] ?? "";
      const bv = b[filters.sortKey] ?? "";
      let cmp: number;
      if (typeof av === "number" && typeof bv === "number") {
        cmp = av - bv;
      } else {
        cmp = String(av).localeCompare(String(bv));
      }
      return filters.sortDir === "asc" ? cmp : -cmp;
    });

    return result;
  }, [experiments, filters, hiddenRuns, showHidden]);

  // Reset page when filters change
  const filteredLen = filtered.length;
  useMemo(() => setPage(1), [filteredLen, filters.search, filters.configFilter, filters.modelFilter, filters.providerFilter, filters.runMode]);

  const paged = useMemo(() => paginate(filtered, page, pageSize), [filtered, page, pageSize]);

  const toggleSort = (key: SortKey) => {
    setFilters((prev) => {
      if (prev.sortKey === key) {
        return { ...prev, sortDir: prev.sortDir === "asc" ? "desc" : "asc" };
      }
      return { ...prev, sortKey: key, sortDir: key === "timestamp" ? "desc" : "asc" };
    });
  };

  const activeFilterCount = [
    filters.configFilter !== "all",
    filters.modelFilter !== "all",
    filters.providerFilter !== "all",
    filters.search !== "",
    filters.runMode !== "official",
  ].filter(Boolean).length;

  const clearFilters = () => {
    setFilters((prev) => ({
      ...prev,
      search: "",
      configFilter: "all",
      modelFilter: "all",
      providerFilter: "all",
      runMode: "official",
    }));
  };

  const toggleRunSelection = (runId: string) => {
    setSelectedRuns((prev) => {
      const next = new Set(prev);
      if (next.has(runId)) {
        next.delete(runId);
      } else if (next.size < 4) {
        next.add(runId);
      }
      return next;
    });
  };

  const toggleHideRun = (runId: string) => {
    setHiddenRuns((prev) => {
      const next = new Set(prev);
      if (next.has(runId)) {
        next.delete(runId);
      } else {
        next.add(runId);
      }
      return next;
    });
  };

  const goToCompare = () => {
    const ids = [...selectedRuns].join(",");
    router.push(`/compare?runs=${encodeURIComponent(ids)}`);
  };

  const SortHeader = ({
    k,
    children,
    className,
  }: {
    k: SortKey;
    children: React.ReactNode;
    className?: string;
  }) => (
    <TableHead
      className={`cursor-pointer select-none ${className ?? ""}`}
      onClick={() => toggleSort(k)}
    >
      {children} {filters.sortKey === k ? (filters.sortDir === "asc" ? "\u2191" : "\u2193") : ""}
    </TableHead>
  );

  return (
    <div className="space-y-4">
      <div className="flex gap-3 flex-wrap items-center">
        <div className="inline-flex rounded-md border border-input bg-background">
          {(["official", "test", "all"] as const).map((mode) => (
            <button
              key={mode}
              onClick={() => updateFilter("runMode", mode)}
              className={`px-3 py-1.5 text-sm font-medium first:rounded-l-md last:rounded-r-md transition-colors ${
                filters.runMode === mode
                  ? "bg-primary text-primary-foreground"
                  : "hover:bg-muted"
              }`}
            >
              {mode === "official" ? "Official" : mode === "test" ? "Test" : "All"}
            </button>
          ))}
        </div>
        <Input
          placeholder="Search model or provider..."
          className="w-64"
          value={filters.search}
          onChange={(e) => updateFilter("search", e.target.value)}
        />
        <Select
          value={filters.configFilter}
          onValueChange={(v) => updateFilter("configFilter", v)}
        >
          <SelectTrigger className="w-36">
            <SelectValue placeholder="Config" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All configs</SelectItem>
            {configTypes.map((ct) => (
              <SelectItem key={ct} value={ct}>
                {ct}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select
          value={filters.modelFilter}
          onValueChange={(v) => updateFilter("modelFilter", v)}
        >
          <SelectTrigger className="w-44">
            <SelectValue placeholder="Model" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All models</SelectItem>
            {modelKeys.map((mk) => (
              <SelectItem key={mk} value={mk}>
                {mk}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select
          value={filters.providerFilter}
          onValueChange={(v) => updateFilter("providerFilter", v)}
        >
          <SelectTrigger className="w-36">
            <SelectValue placeholder="Provider" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All providers</SelectItem>
            {providers.map((p) => (
              <SelectItem key={p} value={p}>
                {p}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <span className="text-sm text-muted-foreground">
          {filtered.length} of {experiments.length} runs
        </span>
        {activeFilterCount > 0 && (
          <button
            onClick={clearFilters}
            className="text-sm text-muted-foreground hover:text-foreground underline underline-offset-2"
          >
            Clear filters
          </button>
        )}
        <ExportButton
          data={filtered.map((e) => ({
            run_id: e.run_id,
            model_key: e.model_key,
            provider: e.provider,
            config: e.baseline_type,
            f1: e.f1,
            f2: e.f2,
            precision: e.precision,
            recall: e.recall,
            avg_jaccard: e.avg_jaccard,
            laziness_rate: e.laziness_rate,
            cost_usd: e.total_cost_usd ?? "",
            duration_seconds: e.duration_seconds ?? "",
            samples: e.sample_count,
            timestamp: e.timestamp ?? "",
          }))}
          filename="experiments"
          label="Export CSV"
        />
      </div>

      {/* Hidden runs toggle */}
      {hiddenRuns.size > 0 && (
        <div className="flex items-center gap-3">
          <button
            onClick={() => setShowHidden(!showHidden)}
            className="text-sm text-muted-foreground hover:text-foreground underline underline-offset-2"
          >
            {showHidden ? "Hide" : "Show"} {hiddenRuns.size} hidden experiment{hiddenRuns.size !== 1 ? "s" : ""}
          </button>
          {showHidden && (
            <button
              onClick={() => setHiddenRuns(new Set())}
              className="text-sm text-muted-foreground hover:text-foreground underline underline-offset-2"
            >
              Unhide all
            </button>
          )}
        </div>
      )}

      {/* Compare Selected bar */}
      {selectedRuns.size > 0 && (
        <div className="flex items-center gap-3 p-3 bg-muted rounded-md">
          <span className="text-sm font-medium">
            {selectedRuns.size} selected (max 4)
          </span>
          <button
            onClick={goToCompare}
            disabled={selectedRuns.size < 2}
            className="px-3 py-1.5 text-sm font-medium rounded-md bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Compare Selected
          </button>
          <button
            onClick={() => setSelectedRuns(new Set())}
            className="text-sm text-muted-foreground hover:text-foreground underline underline-offset-2"
          >
            Clear selection
          </button>
        </div>
      )}

      <div className="border rounded-md">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-10"></TableHead>
              <SortHeader k="model_key">Model</SortHeader>
              <SortHeader k="baseline_type">Config</SortHeader>
              <SortHeader k="timestamp">Date</SortHeader>
              <SortHeader k="f1" className="text-right">F1</SortHeader>
              <SortHeader k="f2" className="text-right">F2</SortHeader>
              <SortHeader k="precision" className="text-right">Precision</SortHeader>
              <SortHeader k="recall" className="text-right">Recall</SortHeader>
              <SortHeader k="avg_jaccard" className="text-right">Jaccard</SortHeader>
              <SortHeader k="laziness_rate" className="text-right">Laziness</SortHeader>
              <SortHeader k="total_cost_usd" className="text-right">Cost</SortHeader>
              <SortHeader k="duration_seconds" className="text-right">Duration</SortHeader>
              <SortHeader k="sample_count" className="text-right">Samples</SortHeader>
              <TableHead className="w-10"></TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {paged.map((exp) => {
              const isHidden = hiddenRuns.has(exp.run_id);
              return (
                <TableRow
                  key={exp.run_id}
                  className={`cursor-pointer hover:bg-muted/50 ${selectedRuns.has(exp.run_id) ? "bg-muted/30" : ""} ${isHidden ? "opacity-50" : ""}`}
                  onClick={() =>
                    router.push(`/experiments/${encodeURIComponent(exp.run_id)}`)
                  }
                >
                  <TableCell className="w-10" onClick={(e) => e.stopPropagation()}>
                    <Checkbox
                      checked={selectedRuns.has(exp.run_id)}
                      onCheckedChange={() => toggleRunSelection(exp.run_id)}
                      disabled={!selectedRuns.has(exp.run_id) && selectedRuns.size >= 4}
                    />
                  </TableCell>
                  <TableCell>
                    <span className="font-medium">{exp.model_key}</span>
                    <div className="text-xs text-muted-foreground">{exp.provider}</div>
                  </TableCell>
                  <TableCell>
                    <Badge variant="secondary">{exp.baseline_type}</Badge>
                  </TableCell>
                  <TableCell className="text-sm text-muted-foreground">
                    {formatDate(exp.timestamp)}
                  </TableCell>
                  <TableCell className="text-right font-mono">{fixed(exp.f1)}</TableCell>
                  <TableCell className="text-right font-mono font-medium">
                    {fixed(exp.f2)}
                  </TableCell>
                  <TableCell className="text-right font-mono">
                    {fixed(exp.precision)}
                  </TableCell>
                  <TableCell className="text-right font-mono">{fixed(exp.recall)}</TableCell>
                  <TableCell className="text-right font-mono">
                    {fixed(exp.avg_jaccard)}
                  </TableCell>
                  <TableCell className="text-right font-mono">
                    {pct(exp.laziness_rate)}
                  </TableCell>
                  <TableCell className="text-right font-mono">
                    {exp.total_cost_usd != null ? usd(exp.total_cost_usd) : "N/A"}
                  </TableCell>
                  <TableCell className="text-right font-mono">
                    {exp.duration_seconds != null ? duration(exp.duration_seconds) : "N/A"}
                  </TableCell>
                  <TableCell className="text-right">{exp.sample_count}</TableCell>
                  <TableCell className="w-10" onClick={(e) => e.stopPropagation()}>
                    <button
                      onClick={() => toggleHideRun(exp.run_id)}
                      className="p-1 rounded hover:bg-muted transition-colors"
                      title={isHidden ? "Unhide experiment" : "Hide experiment"}
                    >
                      {isHidden ? (
                        <svg className="w-4 h-4 text-muted-foreground" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                        </svg>
                      ) : (
                        <svg className="w-4 h-4 text-muted-foreground" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21" />
                        </svg>
                      )}
                    </button>
                  </TableCell>
                </TableRow>
              );
            })}
            {filtered.length === 0 && (
              <TableRow>
                <TableCell
                  colSpan={14}
                  className="text-center text-muted-foreground py-12"
                >
                  No experiments match the current filters.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>

      <Pagination
        totalItems={filtered.length}
        page={page}
        pageSize={pageSize}
        onPageChange={setPage}
        onPageSizeChange={setPageSize}
      />
    </div>
  );
}
