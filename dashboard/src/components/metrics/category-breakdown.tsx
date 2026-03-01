"use client";

import { useMemo, useState } from "react";
import type { SampleSummary } from "@/lib/types";
import { computeCategoryMetrics, type CategoryMetrics } from "@/lib/category-utils";
import { fixed } from "@/lib/format";
import { tierColors } from "@/lib/colors";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";
import { ExportButton } from "@/components/ui/export-button";

interface CategoryBreakdownProps {
  samples: SampleSummary[];
}

type SortKey = keyof CategoryMetrics;

export function CategoryBreakdown({ samples }: CategoryBreakdownProps) {
  const categories = useMemo(() => computeCategoryMetrics(samples), [samples]);
  const [sortKey, setSortKey] = useState<SortKey>("tier");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("asc");

  const sorted = useMemo(() => {
    const tierOrder: Record<string, number> = { common: 0, moderate: 1, rare: 2 };
    return [...categories].sort((a, b) => {
      let cmp: number;
      if (sortKey === "tier") {
        cmp = (tierOrder[a.tier] ?? 3) - (tierOrder[b.tier] ?? 3);
        if (cmp === 0) cmp = a.category.localeCompare(b.category);
      } else if (sortKey === "category") {
        cmp = a.category.localeCompare(b.category);
      } else {
        cmp = (a[sortKey] as number) - (b[sortKey] as number);
      }
      return sortDir === "asc" ? cmp : -cmp;
    });
  }, [categories, sortKey, sortDir]);

  const toggleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDir(key === "category" || key === "tier" ? "asc" : "desc");
    }
  };

  // Chart data: F2 per category, colored by tier
  const chartData = useMemo(
    () =>
      categories.map((c) => ({
        category: c.category.length > 20 ? c.category.slice(0, 18) + "..." : c.category,
        fullCategory: c.category,
        F2: Number((c.f2 * 100).toFixed(1)),
        tier: c.tier,
      })),
    [categories],
  );

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

  if (categories.length === 0) return null;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-medium">Per-Category Breakdown ({categories.length} categories)</h3>
        <ExportButton
          data={sorted.map((c) => ({
            category: c.category,
            tier: c.tier,
            tp: c.tp,
            fp: c.fp,
            fn: c.fn,
            tn: c.tn,
            precision: c.precision,
            recall: c.recall,
            f1: c.f1,
            f2: c.f2,
            jaccard: c.jaccard,
          }))}
          filename="category-breakdown"
          label="Export CSV"
        />
      </div>

      {/* Horizontal bar chart of F2 per category */}
      <div style={{ height: Math.max(300, categories.length * 24) }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData} layout="vertical" margin={{ left: 140, right: 20 }}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis type="number" domain={[0, 100]} fontSize={12} tickFormatter={(v) => `${v}%`} />
            <YAxis type="category" dataKey="category" fontSize={11} width={130} />
            <Tooltip
              formatter={(v) => `${v}%`}
              labelFormatter={(_, payload) => {
                const item = payload?.[0]?.payload;
                return item?.fullCategory ?? "";
              }}
            />
            <Bar dataKey="F2" radius={[0, 2, 2, 0]}>
              {chartData.map((entry, i) => (
                <Cell key={i} fill={tierColors[entry.tier]?.chart ?? "#94a3b8"} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Table */}
      <div className="border rounded-md">
        <Table>
          <TableHeader>
            <TableRow>
              <SortHeader k="category">Category</SortHeader>
              <SortHeader k="tier">Tier</SortHeader>
              <SortHeader k="tp" className="text-right">TP</SortHeader>
              <SortHeader k="fp" className="text-right">FP</SortHeader>
              <SortHeader k="fn" className="text-right">FN</SortHeader>
              <SortHeader k="tn" className="text-right">TN</SortHeader>
              <SortHeader k="precision" className="text-right">Precision</SortHeader>
              <SortHeader k="recall" className="text-right">Recall</SortHeader>
              <SortHeader k="f1" className="text-right">F1</SortHeader>
              <SortHeader k="f2" className="text-right">F2</SortHeader>
              <SortHeader k="jaccard" className="text-right">Jaccard</SortHeader>
            </TableRow>
          </TableHeader>
          <TableBody>
            {sorted.map((c) => {
              const tc = tierColors[c.tier];
              return (
                <TableRow key={c.category}>
                  <TableCell className="font-medium text-sm">{c.category}</TableCell>
                  <TableCell>
                    <Badge variant="outline" className={`${tc?.bg ?? ""} ${tc?.text ?? ""} ${tc?.border ?? ""}`}>
                      {c.tier}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-right">{c.tp}</TableCell>
                  <TableCell className="text-right">{c.fp}</TableCell>
                  <TableCell className="text-right">{c.fn}</TableCell>
                  <TableCell className="text-right">{c.tn}</TableCell>
                  <TableCell className="text-right font-mono">{fixed(c.precision)}</TableCell>
                  <TableCell className="text-right font-mono">{fixed(c.recall)}</TableCell>
                  <TableCell className="text-right font-mono">{fixed(c.f1)}</TableCell>
                  <TableCell className="text-right font-mono font-medium">{fixed(c.f2)}</TableCell>
                  <TableCell className="text-right font-mono">{fixed(c.jaccard)}</TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
