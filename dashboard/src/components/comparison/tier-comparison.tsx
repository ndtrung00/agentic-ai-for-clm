"use client";

import { useMemo } from "react";
import type { ExperimentSummary } from "@/lib/types";
import { fixed } from "@/lib/format";
import { tierColors } from "@/lib/colors";
import { RUN_COLORS } from "./run-selector";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";

interface TierComparisonProps {
  experiments: ExperimentSummary[];
}

const TIER_ORDER = ["common", "moderate", "rare"];

export function TierComparison({ experiments }: TierComparisonProps) {
  // Build chart data: one entry per tier, with F2 values for each run
  const chartData = useMemo(() => {
    return TIER_ORDER.map((tier) => {
      const entry: Record<string, string | number> = {
        tier: tier.charAt(0).toUpperCase() + tier.slice(1),
      };
      experiments.forEach((exp, i) => {
        const tm = exp.per_tier[tier];
        entry[`F2_${i}`] = tm ? Number((tm.f2 * 100).toFixed(1)) : 0;
      });
      return entry;
    });
  }, [experiments]);

  return (
    <div className="space-y-6">
      {/* Grouped bar chart: F2 per tier per run */}
      <div>
        <h3 className="text-sm font-medium mb-3">F2 Score by Tier</h3>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData} barGap={2}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="tier" fontSize={12} />
              <YAxis domain={[0, 100]} fontSize={12} tickFormatter={(v) => `${v}%`} />
              <Tooltip formatter={(v) => `${v}%`} />
              <Legend />
              {experiments.map((exp, i) => (
                <Bar
                  key={exp.run_id}
                  dataKey={`F2_${i}`}
                  name={`${exp.config.baseline_type}/${exp.config.model_key}`}
                  fill={RUN_COLORS[i]}
                  radius={[2, 2, 0, 0]}
                />
              ))}
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Detailed table */}
      <div className="border rounded-md overflow-x-auto">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Tier</TableHead>
              <TableHead>Metric</TableHead>
              {experiments.map((exp, i) => (
                <TableHead key={exp.run_id} className="text-right">
                  <div className="flex items-center justify-end gap-1">
                    <span
                      className="w-2 h-2 rounded-full"
                      style={{ backgroundColor: RUN_COLORS[i] }}
                    />
                    <span className="truncate max-w-[100px] text-xs">
                      {exp.config.baseline_type}
                    </span>
                  </div>
                </TableHead>
              ))}
            </TableRow>
          </TableHeader>
          <TableBody>
            {TIER_ORDER.map((tier) => {
              const tc = tierColors[tier];
              return ["f1", "f2", "avg_jaccard"].map((metric, mi) => (
                <TableRow key={`${tier}-${metric}`}>
                  {mi === 0 && (
                    <TableCell rowSpan={3} className="align-top">
                      <Badge variant="outline" className={`${tc?.bg ?? ""} ${tc?.text ?? ""} ${tc?.border ?? ""}`}>
                        {tier}
                      </Badge>
                    </TableCell>
                  )}
                  <TableCell className="text-xs text-muted-foreground uppercase">
                    {metric === "avg_jaccard" ? "Jaccard" : metric.toUpperCase()}
                  </TableCell>
                  {experiments.map((exp) => {
                    const tm = exp.per_tier[tier];
                    const val = tm ? tm[metric as keyof typeof tm] : 0;
                    return (
                      <TableCell key={exp.run_id} className="text-right font-mono text-sm">
                        {fixed(val as number)}
                      </TableCell>
                    );
                  })}
                </TableRow>
              ));
            })}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
