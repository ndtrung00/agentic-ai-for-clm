"use client";

import type { Metrics } from "@/lib/types";
import { classificationColors } from "@/lib/colors";
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend } from "recharts";

interface ClassificationPieProps {
  metrics: Metrics;
}

export function ClassificationPie({ metrics }: ClassificationPieProps) {
  const data = [
    { name: "TP", value: metrics.tp },
    { name: "TN", value: metrics.tn },
    { name: "FP", value: metrics.fp },
    { name: "FN", value: metrics.fn },
  ].filter((d) => d.value > 0);

  return (
    <div>
      <h3 className="text-sm font-medium mb-2">Classification Distribution</h3>
      <div className="h-52">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={data}
              cx="50%"
              cy="50%"
              outerRadius={70}
              dataKey="value"
              label={({ name, value }) => `${name}: ${value}`}
              fontSize={12}
            >
              {data.map((entry) => (
                <Cell key={entry.name} fill={classificationColors[entry.name]?.chart ?? "#888"} />
              ))}
            </Pie>
            <Tooltip />
            <Legend />
          </PieChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
