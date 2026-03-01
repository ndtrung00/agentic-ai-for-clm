"use client";

import { useMemo } from "react";
import type { SampleSummary } from "@/lib/types";
import { classificationColors } from "@/lib/colors";
import {
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";

interface LengthPerformanceProps {
  samples: SampleSummary[];
}

export function LengthPerformance({ samples }: LengthPerformanceProps) {
  // Group by classification for different colored scatter points
  const data = useMemo(() => {
    const groups: Record<string, { x: number; y: number; category: string }[]> = {
      TP: [],
      TN: [],
      FP: [],
      FN: [],
    };

    for (const s of samples) {
      if (s.input_tokens == null) continue;
      const cls = s.classification.toUpperCase();
      if (groups[cls]) {
        groups[cls].push({
          x: s.input_tokens,
          y: s.jaccard ?? 0,
          category: s.category,
        });
      }
    }

    return groups;
  }, [samples]);

  // Don't render if no samples have input_tokens
  const totalPoints = Object.values(data).reduce((sum, arr) => sum + arr.length, 0);
  if (totalPoints === 0) return null;

  return (
    <div className="space-y-2">
      <h3 className="text-sm font-medium">Input Length vs Jaccard Score</h3>
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <ScatterChart margin={{ bottom: 10, left: 10 }}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis
              type="number"
              dataKey="x"
              name="Input Tokens"
              fontSize={11}
              tickFormatter={(v) => v >= 1000 ? `${(v / 1000).toFixed(0)}k` : `${v}`}
            />
            <YAxis
              type="number"
              dataKey="y"
              name="Jaccard"
              domain={[0, 1]}
              fontSize={11}
            />
            <Tooltip />
            <Legend />
            {(["TP", "TN", "FP", "FN"] as const).map((cls) =>
              data[cls].length > 0 ? (
                <Scatter
                  key={cls}
                  name={cls}
                  data={data[cls]}
                  fill={classificationColors[cls]?.chart ?? "#94a3b8"}
                  opacity={0.7}
                />
              ) : null,
            )}
          </ScatterChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
