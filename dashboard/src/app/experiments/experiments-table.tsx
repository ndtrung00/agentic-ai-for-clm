"use client";

import { useState, useMemo } from "react";
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

export function ExperimentsTable({ experiments }: ExperimentsTableProps) {
  const router = useRouter();
  const [search, setSearch] = useState("");
  const [configFilter, setConfigFilter] = useState<string>("all");
  const [sortKey, setSortKey] = useState<SortKey>("timestamp");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");

  // Unique config types for filter dropdown
  const configTypes = useMemo(
    () => [...new Set(experiments.map((e) => e.baseline_type))].sort(),
    [experiments],
  );

  const filtered = useMemo(() => {
    let result = [...experiments];

    if (configFilter !== "all") {
      result = result.filter((e) => e.baseline_type === configFilter);
    }

    if (search) {
      const q = search.toLowerCase();
      result = result.filter(
        (e) =>
          e.model_key.toLowerCase().includes(q) ||
          e.provider.toLowerCase().includes(q) ||
          e.run_id.toLowerCase().includes(q),
      );
    }

    result.sort((a, b) => {
      const av = a[sortKey] ?? "";
      const bv = b[sortKey] ?? "";
      let cmp: number;
      if (typeof av === "number" && typeof bv === "number") {
        cmp = av - bv;
      } else {
        cmp = String(av).localeCompare(String(bv));
      }
      return sortDir === "asc" ? cmp : -cmp;
    });

    return result;
  }, [experiments, configFilter, search, sortKey, sortDir]);

  const toggleSort = (key: SortKey) => {
    if (sortKey === key) setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    else {
      setSortKey(key);
      setSortDir(key === "timestamp" ? "desc" : "asc");
    }
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
      {children} {sortKey === k ? (sortDir === "asc" ? "\u2191" : "\u2193") : ""}
    </TableHead>
  );

  return (
    <div className="space-y-4">
      <div className="flex gap-3 flex-wrap">
        <Input
          placeholder="Search model or provider..."
          className="w-64"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <Select value={configFilter} onValueChange={setConfigFilter}>
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
        <span className="text-sm text-muted-foreground self-center">
          {filtered.length} of {experiments.length} runs
        </span>
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
