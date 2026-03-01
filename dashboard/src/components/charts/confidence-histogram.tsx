"use client";

import { useMemo } from "react";
import type { SampleSummary } from "@/lib/types";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

interface ConfidenceHistogramProps {
  samples: SampleSummary[];
}

export function ConfidenceHistogram({ samples }: ConfidenceHistogramProps) {
  const histData = useMemo(() => {
    // Check if any samples have confidence data (from output.confidence in intermediate JSONL)
    // SampleSummary doesn't have confidence directly, but we can check classification distribution
    // as a proxy. For now we check if samples have a jaccard > 0 (indicating actual data).

    // Build jaccard histogram as a proxy for score distribution
    const bins = Array.from({ length: 10 }, (_, i) => ({
      range: `${(i * 0.1).toFixed(1)}-${((i + 1) * 0.1).toFixed(1)}`,
      count: 0,
      tp: 0,
      fp: 0,
      fn: 0,
      tn: 0,
    }));

    for (const s of samples) {
      const j = s.jaccard ?? 0;
      const binIdx = Math.min(9, Math.floor(j * 10));
      bins[binIdx].count++;
      const cls = s.classification.toUpperCase();
      if (cls === "TP") bins[binIdx].tp++;
      else if (cls === "FP") bins[binIdx].fp++;
      else if (cls === "FN") bins[binIdx].fn++;
      else if (cls === "TN") bins[binIdx].tn++;
    }

    return bins;
  }, [samples]);

  // Don't render if all samples have jaccard = 0 (no meaningful distribution)
  const hasData = histData.some((b) => b.count > 0 && b.range !== "0.0-0.1");
  if (!hasData) return null;

  return (
    <div className="space-y-2">
      <h3 className="text-sm font-medium">Jaccard Score Distribution</h3>
      <div className="h-48">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={histData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="range" fontSize={10} />
            <YAxis fontSize={11} allowDecimals={false} />
            <Tooltip />
            <Bar dataKey="tp" name="TP" fill="#22c55e" stackId="cls" />
            <Bar dataKey="tn" name="TN" fill="#3b82f6" stackId="cls" />
            <Bar dataKey="fp" name="FP" fill="#f97316" stackId="cls" />
            <Bar dataKey="fn" name="FN" fill="#ef4444" stackId="cls" radius={[2, 2, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
