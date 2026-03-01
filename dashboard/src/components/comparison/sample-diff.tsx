"use client";

import { useMemo, useState } from "react";
import type { ExperimentSummary } from "@/lib/types";
import { fixed } from "@/lib/format";
import { tierColors, classificationColors } from "@/lib/colors";
import { RUN_COLORS } from "./run-selector";
import { Badge } from "@/components/ui/badge";
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
import { Pagination, paginate } from "@/components/ui/pagination";

interface SampleDiffProps {
  experiments: ExperimentSummary[];
}

type DiffFilter = "all" | "disagreements" | "fn_improvements" | "fn_regressions";

export function SampleDiff({ experiments }: SampleDiffProps) {
  const [diffFilter, setDiffFilter] = useState<DiffFilter>("disagreements");
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(50);

  // Build a unified sample map keyed by category
  const sampleRows = useMemo(() => {
    // Collect all categories across experiments
    const categorySet = new Set<string>();
    const sampleMaps = experiments.map((exp) => {
      const map = new Map<string, { classification: string; jaccard: number; tier: string }>();
      for (const s of exp.samples) {
        map.set(s.category, { classification: s.classification, jaccard: s.jaccard, tier: s.tier });
        categorySet.add(s.category);
      }
      return map;
    });

    const rows = [...categorySet].map((category) => {
      const perRun = sampleMaps.map((map) => map.get(category) ?? null);
      const tier = perRun.find((r) => r !== null)?.tier ?? "unknown";
      const classifications = perRun.map((r) => r?.classification ?? null);
      const hasDisagreement = new Set(classifications.filter(Boolean)).size > 1;

      // Check if any run improved from FN (in first run) to non-FN
      const baselineIsFN = classifications[0] === "FN";
      const anyImproved = baselineIsFN && classifications.slice(1).some((c) => c !== null && c !== "FN");
      const anyRegressed = classifications[0] !== "FN" && classifications.slice(1).some((c) => c === "FN");

      return { category, tier, perRun, hasDisagreement, anyImproved, anyRegressed };
    });

    // Sort by tier order then category
    const tierOrder: Record<string, number> = { common: 0, moderate: 1, rare: 2 };
    rows.sort((a, b) => {
      const ta = tierOrder[a.tier] ?? 3;
      const tb = tierOrder[b.tier] ?? 3;
      if (ta !== tb) return ta - tb;
      return a.category.localeCompare(b.category);
    });

    return rows;
  }, [experiments]);

  const filtered = useMemo(() => {
    switch (diffFilter) {
      case "disagreements":
        return sampleRows.filter((r) => r.hasDisagreement);
      case "fn_improvements":
        return sampleRows.filter((r) => r.anyImproved);
      case "fn_regressions":
        return sampleRows.filter((r) => r.anyRegressed);
      default:
        return sampleRows;
    }
  }, [sampleRows, diffFilter]);

  // Reset page when filter changes
  const filteredLen = filtered.length;
  useMemo(() => setPage(1), [filteredLen, diffFilter]);

  const paged = useMemo(() => paginate(filtered, page, pageSize), [filtered, page, pageSize]);

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <h3 className="text-sm font-medium">Sample-Level Comparison</h3>
        <Select value={diffFilter} onValueChange={(v) => setDiffFilter(v as DiffFilter)}>
          <SelectTrigger className="w-48">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All samples</SelectItem>
            <SelectItem value="disagreements">Disagreements only</SelectItem>
            <SelectItem value="fn_improvements">FN improvements</SelectItem>
            <SelectItem value="fn_regressions">FN regressions</SelectItem>
          </SelectContent>
        </Select>
        <span className="text-xs text-muted-foreground">
          {filtered.length} of {sampleRows.length} categories
        </span>
      </div>

      <div className="border rounded-md overflow-x-auto">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="min-w-[180px]">Category</TableHead>
              <TableHead>Tier</TableHead>
              {experiments.map((exp, i) => (
                <TableHead key={exp.run_id} className="text-center min-w-[120px]">
                  <div className="flex items-center justify-center gap-1">
                    <span
                      className="w-2 h-2 rounded-full"
                      style={{ backgroundColor: RUN_COLORS[i] }}
                    />
                    <span className="text-xs truncate max-w-[80px]">
                      {exp.config.baseline_type}/{exp.config.model_key}
                    </span>
                  </div>
                </TableHead>
              ))}
            </TableRow>
          </TableHeader>
          <TableBody>
            {paged.map((row) => {
              const tc = tierColors[row.tier];
              return (
                <TableRow key={row.category}>
                  <TableCell className="font-medium text-xs">{row.category}</TableCell>
                  <TableCell>
                    <Badge
                      variant="outline"
                      className={`text-xs ${tc?.bg ?? ""} ${tc?.text ?? ""} ${tc?.border ?? ""}`}
                    >
                      {row.tier}
                    </Badge>
                  </TableCell>
                  {row.perRun.map((r, i) => {
                    if (!r) {
                      return (
                        <TableCell key={i} className="text-center text-muted-foreground text-xs">
                          -
                        </TableCell>
                      );
                    }
                    const cc = classificationColors[r.classification];
                    return (
                      <TableCell key={i} className="text-center">
                        <div className="flex flex-col items-center gap-0.5">
                          <Badge
                            variant="outline"
                            className={`text-xs ${cc?.bg ?? ""} ${cc?.text ?? ""} ${cc?.border ?? ""}`}
                          >
                            {r.classification}
                          </Badge>
                          <span className="text-xs text-muted-foreground font-mono">
                            J:{fixed(r.jaccard)}
                          </span>
                        </div>
                      </TableCell>
                    );
                  })}
                </TableRow>
              );
            })}
            {filtered.length === 0 && (
              <TableRow>
                <TableCell
                  colSpan={2 + experiments.length}
                  className="text-center text-muted-foreground py-8"
                >
                  No samples match the selected filter.
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
