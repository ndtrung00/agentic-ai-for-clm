"use client";

import { useMemo } from "react";
import type { ExperimentSummary } from "@/lib/types";
import { bootstrapCI, type BootstrapCI } from "@/lib/statistics";
import { fixed } from "@/lib/format";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { RUN_COLORS } from "./run-selector";

interface StatisticalSummaryProps {
  experiments: ExperimentSummary[];
}

type MetricKey = "f1" | "f2" | "jaccard";

const METRICS: { key: MetricKey; label: string }[] = [
  { key: "f2", label: "F2 Score" },
  { key: "f1", label: "F1 Score" },
  { key: "jaccard", label: "Avg Jaccard" },
];

function CIBar({ ci, color, minVal, maxVal }: { ci: BootstrapCI; color: string; minVal: number; maxVal: number }) {
  const range = maxVal - minVal || 1;
  const leftPct = ((ci.lower - minVal) / range) * 100;
  const widthPct = ((ci.upper - ci.lower) / range) * 100;
  const meanPct = ((ci.mean - minVal) / range) * 100;

  return (
    <div className="relative h-5 w-full bg-muted rounded">
      {/* CI range */}
      <div
        className="absolute top-1 h-3 rounded opacity-30"
        style={{
          left: `${Math.max(0, leftPct)}%`,
          width: `${Math.min(100, widthPct)}%`,
          backgroundColor: color,
        }}
      />
      {/* Mean dot */}
      <div
        className="absolute top-0.5 w-2 h-4 rounded-sm"
        style={{
          left: `${Math.max(0, Math.min(98, meanPct))}%`,
          backgroundColor: color,
        }}
      />
    </div>
  );
}

export function StatisticalSummary({ experiments }: StatisticalSummaryProps) {
  const results = useMemo(() => {
    return METRICS.map((m) => {
      const cis = experiments.map((exp) => bootstrapCI(exp.samples, m.key));
      return { metric: m, cis };
    });
  }, [experiments]);

  if (experiments.length < 2) return null;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm">Statistical Comparison (Bootstrap 95% CI, n=1000)</CardTitle>
        <p className="text-xs text-muted-foreground">
          Deltas relative to first run. &quot;Sig&quot; = non-overlapping confidence intervals.
        </p>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          <table className="text-sm w-full">
            <thead>
              <tr className="border-b">
                <th className="text-left py-2 pr-4">Metric</th>
                {experiments.map((exp, i) => (
                  <th key={exp.run_id} className="text-center px-3 min-w-[160px]">
                    <div className="flex items-center justify-center gap-1">
                      <span
                        className="w-2 h-2 rounded-full"
                        style={{ backgroundColor: RUN_COLORS[i] }}
                      />
                      <span className="text-xs truncate max-w-[100px]">
                        {exp.config.baseline_type}/{exp.config.model_key}
                      </span>
                    </div>
                  </th>
                ))}
                {experiments.length === 2 && (
                  <>
                    <th className="text-center px-3">Delta</th>
                    <th className="text-center px-3">Sig?</th>
                  </>
                )}
              </tr>
            </thead>
            <tbody>
              {results.map(({ metric, cis }) => {
                // Compute global min/max for CI bars
                const allVals = cis.flatMap((ci) => [ci.lower, ci.upper]);
                const minVal = Math.min(...allVals) * 0.95;
                const maxVal = Math.max(...allVals) * 1.05;
                const delta = experiments.length === 2 ? cis[1].mean - cis[0].mean : 0;
                const significant =
                  experiments.length === 2 &&
                  (cis[0].upper < cis[1].lower || cis[1].upper < cis[0].lower);

                return (
                  <tr key={metric.key} className="border-b last:border-0">
                    <td className="py-3 pr-4 font-medium">{metric.label}</td>
                    {cis.map((ci, i) => (
                      <td key={experiments[i].run_id} className="text-center px-3">
                        <div className="space-y-1">
                          <CIBar ci={ci} color={RUN_COLORS[i]} minVal={minVal} maxVal={maxVal} />
                          <div className="text-xs font-mono">
                            {fixed(ci.mean)} [{fixed(ci.lower)}, {fixed(ci.upper)}]
                          </div>
                        </div>
                      </td>
                    ))}
                    {experiments.length === 2 && (
                      <>
                        <td className="text-center px-3">
                          <span
                            className={`text-xs font-mono font-medium ${
                              delta > 0 ? "text-green-600" : delta < 0 ? "text-red-600" : ""
                            }`}
                          >
                            {delta >= 0 ? "+" : ""}{fixed(delta)}
                          </span>
                        </td>
                        <td className="text-center px-3">
                          <span
                            className={`text-xs font-medium ${significant ? "text-green-600" : "text-muted-foreground"}`}
                          >
                            {significant ? "Yes" : "No"}
                          </span>
                        </td>
                      </>
                    )}
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  );
}
