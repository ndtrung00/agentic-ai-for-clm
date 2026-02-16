import type { Metrics } from "@/lib/types";
import { MetricCard } from "./metric-card";
import { pct, fixed } from "@/lib/format";

interface MetricsGridProps {
  metrics: Metrics;
}

export function MetricsGrid({ metrics }: MetricsGridProps) {
  return (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
      <MetricCard label="F1 Score" value={fixed(metrics.f1)} highlight />
      <MetricCard label="F2 Score" value={fixed(metrics.f2)} highlight />
      <MetricCard label="Precision" value={fixed(metrics.precision)} />
      <MetricCard label="Recall" value={fixed(metrics.recall)} />
      <MetricCard label="Avg Jaccard" value={fixed(metrics.avg_jaccard)} />
      <MetricCard label="Laziness Rate" value={pct(metrics.laziness_rate)} sublabel={`${metrics.fn} FN / ${metrics.tp + metrics.fn} positive`} />
    </div>
  );
}
