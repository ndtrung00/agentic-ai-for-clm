"use client";

import { useState, useMemo, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import type { ExperimentListItem } from "@/lib/types";
import { pct, fixed, usd, formatDate } from "@/lib/format";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
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

interface ExperimentsTableProps {
  experiments: ExperimentListItem[];
}

type SortKey = keyof ExperimentListItem;

const STORAGE_KEY = "experiments-table-filters";

interface FilterState {
  search: string;
  configFilter: string;
  modelFilter: string;
  providerFilter: string;
  sortKey: SortKey;
  sortDir: "asc" | "desc";
}

const DEFAULT_FILTERS: FilterState = {
  search: "",
  configFilter: "all",
  modelFilter: "all",
  providerFilter: "all",
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

export function ExperimentsTable({ experiments }: ExperimentsTableProps) {
  const router = useRouter();
  const [filters, setFilters] = useState<FilterState>(DEFAULT_FILTERS);
  const [hydrated, setHydrated] = useState(false);

  // Load from localStorage on mount
  useEffect(() => {
    setFilters(loadFilters());
    setHydrated(true);
  }, []);

  // Save to localStorage on change (after hydration)
  useEffect(() => {
    if (hydrated) saveFilters(filters);
  }, [filters, hydrated]);

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
  }, [experiments, filters]);

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
  ].filter(Boolean).length;

  const clearFilters = () => {
    setFilters((prev) => ({
      ...prev,
      search: "",
      configFilter: "all",
      modelFilter: "all",
      providerFilter: "all",
    }));
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
      </div>

      <div className="border rounded-md">
        <Table>
          <TableHeader>
            <TableRow>
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
              <SortHeader k="sample_count" className="text-right">Samples</SortHeader>
            </TableRow>
          </TableHeader>
          <TableBody>
            {filtered.map((exp) => (
              <TableRow
                key={exp.run_id}
                className="cursor-pointer hover:bg-muted/50"
                onClick={() =>
                  router.push(`/experiments/${encodeURIComponent(exp.run_id)}`)
                }
              >
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
                <TableCell className="text-right">{exp.sample_count}</TableCell>
              </TableRow>
            ))}
            {filtered.length === 0 && (
              <TableRow>
                <TableCell
                  colSpan={11}
                  className="text-center text-muted-foreground py-12"
                >
                  No experiments match the current filters.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
