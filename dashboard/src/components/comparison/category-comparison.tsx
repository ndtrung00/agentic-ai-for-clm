"use client";

import { useMemo, useState } from "react";
import type { ExperimentSummary } from "@/lib/types";
import { computeCategoryMetrics } from "@/lib/category-utils";
import { fixed } from "@/lib/format";
import { tierColors } from "@/lib/colors";
import { RUN_COLORS } from "./run-selector";
import { Badge } from "@/components/ui/badge";

interface CategoryComparisonProps {
  experiments: ExperimentSummary[];
}

type MetricKey = "f2" | "f1" | "jaccard" | "precision" | "recall";

export function CategoryComparison({ experiments }: CategoryComparisonProps) {
  const [metric, setMetric] = useState<MetricKey>("f2");

  // Compute per-category metrics for each experiment
  const perExpCategories = useMemo(
    () =>
      experiments.map((exp) => {
        const cats = computeCategoryMetrics(exp.samples);
        const map = new Map(cats.map((c) => [c.category, c]));
        return { exp, cats, map };
      }),
    [experiments],
  );

  // Union of all categories, sorted by tier then name
  const allCategories = useMemo(() => {
    const categorySet = new Map<string, string>(); // category -> tier
    for (const { cats } of perExpCategories) {
      for (const c of cats) {
        if (!categorySet.has(c.category)) categorySet.set(c.category, c.tier);
      }
    }
    const tierOrder: Record<string, number> = { common: 0, moderate: 1, rare: 2 };
    return [...categorySet.entries()]
      .sort(([aCat, aTier], [bCat, bTier]) => {
        const ta = tierOrder[aTier] ?? 3;
        const tb = tierOrder[bTier] ?? 3;
        if (ta !== tb) return ta - tb;
        return aCat.localeCompare(bCat);
      })
      .map(([cat, tier]) => ({ category: cat, tier }));
  }, [perExpCategories]);

  // Color scale: 0 = red, 0.5 = yellow, 1.0 = green
  function heatColor(value: number): string {
    const clamped = Math.max(0, Math.min(1, value));
    if (clamped < 0.5) {
      // red to yellow
      const t = clamped / 0.5;
      const r = 239;
      const g = Math.round(68 + t * (163 - 68));
      const b = Math.round(68 - t * 68);
      return `rgb(${r}, ${g}, ${b})`;
    }
    // yellow to green
    const t = (clamped - 0.5) / 0.5;
    const r = Math.round(239 - t * (239 - 34));
    const g = Math.round(163 + t * (197 - 163));
    const b = Math.round(0 + t * 94);
    return `rgb(${r}, ${g}, ${b})`;
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-medium">Category Heatmap</h3>
        <div className="flex items-center gap-2">
          <span className="text-xs text-muted-foreground">Metric:</span>
          {(["f2", "f1", "precision", "recall", "jaccard"] as MetricKey[]).map((m) => (
            <button
              key={m}
              onClick={() => setMetric(m)}
              className={`text-xs px-2 py-1 rounded ${
                metric === m ? "bg-primary text-primary-foreground" : "bg-muted hover:bg-muted/80"
              }`}
            >
              {m === "jaccard" ? "Jaccard" : m.toUpperCase()}
            </button>
          ))}
        </div>
      </div>

      <div className="overflow-x-auto border rounded-md">
        <table className="text-sm w-full">
          <thead>
            <tr className="border-b bg-muted/30">
              <th className="text-left py-2 px-3 sticky left-0 bg-muted/30 min-w-[180px]">Category</th>
              <th className="text-left py-2 px-2 w-20">Tier</th>
              {experiments.map((exp, i) => (
                <th key={exp.run_id} className="text-center py-2 px-3 min-w-[80px]">
                  <div className="flex items-center justify-center gap-1">
                    <span
                      className="w-2 h-2 rounded-full"
                      style={{ backgroundColor: RUN_COLORS[i] }}
                    />
                    <span className="truncate max-w-[80px] text-xs font-medium">
                      {exp.config.baseline_type}
                    </span>
                  </div>
                  <div className="text-xs text-muted-foreground font-normal truncate">
                    {exp.config.model_key}
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {allCategories.map(({ category, tier }) => {
              const tc = tierColors[tier];
              return (
                <tr key={category} className="border-b last:border-0 hover:bg-muted/20">
                  <td className="py-1.5 px-3 sticky left-0 bg-background font-medium text-xs">
                    {category}
                  </td>
                  <td className="py-1.5 px-2">
                    <Badge
                      variant="outline"
                      className={`text-xs ${tc?.bg ?? ""} ${tc?.text ?? ""} ${tc?.border ?? ""}`}
                    >
                      {tier}
                    </Badge>
                  </td>
                  {perExpCategories.map(({ exp, map }, i) => {
                    const catMetrics = map.get(category);
                    const value = catMetrics ? catMetrics[metric] : null;
                    return (
                      <td
                        key={exp.run_id}
                        className="text-center py-1.5 px-3 font-mono text-xs"
                        style={
                          value != null
                            ? { backgroundColor: heatColor(value), color: value > 0.6 ? "#fff" : "#000" }
                            : {}
                        }
                      >
                        {value != null ? fixed(value) : "-"}
                      </td>
                    );
                  })}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Legend */}
      <div className="flex items-center gap-2 text-xs text-muted-foreground">
        <span>Scale:</span>
        <div className="flex h-4 w-48 rounded overflow-hidden">
          {Array.from({ length: 20 }, (_, i) => (
            <div key={i} className="flex-1" style={{ backgroundColor: heatColor(i / 19) }} />
          ))}
        </div>
        <span>0.0</span>
        <span className="ml-auto">1.0</span>
      </div>
    </div>
  );
}
