"use client";

import type { ExperimentSummary, Metrics } from "@/lib/types";
import { fixed, pct, duration, usd } from "@/lib/format";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { RUN_COLORS } from "./run-selector";

interface MetricsComparisonProps {
  experiments: ExperimentSummary[];
}

interface MetricDef {
  key: keyof Metrics;
  label: string;
  format: (v: number) => string;
  higherBetter: boolean;
}

const METRICS: MetricDef[] = [
  { key: "f2", label: "F2 Score", format: fixed, higherBetter: true },
  { key: "f1", label: "F1 Score", format: fixed, higherBetter: true },
  { key: "precision", label: "Precision", format: fixed, higherBetter: true },
  { key: "recall", label: "Recall", format: fixed, higherBetter: true },
  { key: "avg_jaccard", label: "Avg Jaccard", format: fixed, higherBetter: true },
  { key: "laziness_rate", label: "Laziness Rate", format: pct, higherBetter: false },
];

function DeltaArrow({ value, higherBetter }: { value: number; higherBetter: boolean }) {
  if (Math.abs(value) < 0.001) return <span className="text-muted-foreground text-xs">--</span>;
  const isPositive = value > 0;
  const isGood = higherBetter ? isPositive : !isPositive;
  return (
    <span className={`text-xs font-medium ${isGood ? "text-green-600" : "text-red-600"}`}>
      {isPositive ? "\u25B2" : "\u25BC"} {Math.abs(value).toFixed(3)}
    </span>
  );
}

export function MetricsComparison({ experiments }: MetricsComparisonProps) {
  // Use first experiment as baseline for delta computation
  const baseline = experiments[0];

  return (
    <div className="space-y-4">
      <p className="text-xs text-muted-foreground">
        Deltas shown relative to first selected run ({baseline.config.baseline_type} / {baseline.config.model_key}).
      </p>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {METRICS.map((m) => (
          <Card key={m.key}>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm">{m.label}</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              {experiments.map((exp, i) => {
                const value = exp.metrics[m.key] as number;
                const delta = i === 0 ? 0 : value - (baseline.metrics[m.key] as number);
                return (
                  <div key={exp.run_id} className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span
                        className="w-2.5 h-2.5 rounded-full flex-shrink-0"
                        style={{ backgroundColor: RUN_COLORS[i] }}
                      />
                      <span className="text-xs truncate max-w-[140px]">
                        {exp.config.baseline_type} / {exp.config.model_key}
                      </span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="font-mono font-medium text-sm">{m.format(value)}</span>
                      {i > 0 && <DeltaArrow value={delta} higherBetter={m.higherBetter} />}
                    </div>
                  </div>
                );
              })}
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Confusion matrix comparison */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Classification Counts</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="text-sm w-full">
              <thead>
                <tr className="border-b">
                  <th className="text-left py-2 pr-4">Run</th>
                  <th className="text-right px-3">TP</th>
                  <th className="text-right px-3">TN</th>
                  <th className="text-right px-3">FP</th>
                  <th className="text-right px-3">FN</th>
                  <th className="text-right px-3">Total</th>
                  <th className="text-right px-3">Duration</th>
                  <th className="text-right px-3">Cost</th>
                </tr>
              </thead>
              <tbody>
                {experiments.map((exp, i) => (
                  <tr key={exp.run_id} className="border-b last:border-0">
                    <td className="py-2 pr-4">
                      <div className="flex items-center gap-2">
                        <span
                          className="w-2.5 h-2.5 rounded-full flex-shrink-0"
                          style={{ backgroundColor: RUN_COLORS[i] }}
                        />
                        <span className="truncate max-w-[180px]">
                          {exp.config.baseline_type} / {exp.config.model_key}
                        </span>
                      </div>
                    </td>
                    <td className="text-right px-3 text-green-600">{exp.metrics.tp}</td>
                    <td className="text-right px-3 text-blue-600">{exp.metrics.tn}</td>
                    <td className="text-right px-3 text-orange-600">{exp.metrics.fp}</td>
                    <td className="text-right px-3 text-red-600">{exp.metrics.fn}</td>
                    <td className="text-right px-3">
                      {exp.metrics.tp + exp.metrics.tn + exp.metrics.fp + exp.metrics.fn}
                    </td>
                    <td className="text-right px-3 font-mono">
                      {exp.diagnostics?.duration_seconds != null ? duration(exp.diagnostics.duration_seconds) : "N/A"}
                    </td>
                    <td className="text-right px-3 font-mono">
                      {exp.diagnostics?.total_cost_usd != null ? usd(exp.diagnostics.total_cost_usd) : "N/A"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
