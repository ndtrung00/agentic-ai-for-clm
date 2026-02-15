import type { Metrics } from "@/lib/types";

interface ConfusionMatrixProps {
  metrics: Metrics;
}

export function ConfusionMatrix({ metrics }: ConfusionMatrixProps) {
  const total = metrics.tp + metrics.fp + metrics.fn + metrics.tn;
  const cellPct = (v: number) => total > 0 ? `${((v / total) * 100).toFixed(1)}%` : "0%";

  return (
    <div>
      <h3 className="text-sm font-medium mb-2">Confusion Matrix</h3>
      <div className="grid grid-cols-3 gap-0 text-center text-sm max-w-xs">
        {/* Header row */}
        <div />
        <div className="p-2 font-medium text-muted-foreground">Pred Positive</div>
        <div className="p-2 font-medium text-muted-foreground">Pred Negative</div>

        {/* Actual positive row */}
        <div className="p-2 font-medium text-muted-foreground text-right">Actual Positive</div>
        <div className="p-3 bg-green-50 border border-green-200 rounded-tl-md">
          <div className="font-bold text-green-700 text-lg">{metrics.tp}</div>
          <div className="text-xs text-green-600">TP ({cellPct(metrics.tp)})</div>
        </div>
        <div className="p-3 bg-red-50 border border-red-200 rounded-tr-md">
          <div className="font-bold text-red-700 text-lg">{metrics.fn}</div>
          <div className="text-xs text-red-600">FN ({cellPct(metrics.fn)})</div>
        </div>

        {/* Actual negative row */}
        <div className="p-2 font-medium text-muted-foreground text-right">Actual Negative</div>
        <div className="p-3 bg-orange-50 border border-orange-200 rounded-bl-md">
          <div className="font-bold text-orange-700 text-lg">{metrics.fp}</div>
          <div className="text-xs text-orange-600">FP ({cellPct(metrics.fp)})</div>
        </div>
        <div className="p-3 bg-blue-50 border border-blue-200 rounded-br-md">
          <div className="font-bold text-blue-700 text-lg">{metrics.tn}</div>
          <div className="text-xs text-blue-600">TN ({cellPct(metrics.tn)})</div>
        </div>
      </div>
    </div>
  );
}
