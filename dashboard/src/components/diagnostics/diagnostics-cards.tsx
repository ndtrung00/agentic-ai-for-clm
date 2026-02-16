"use client";

import type { DiagnosticsSummary } from "@/lib/types";
import { MetricCard } from "@/components/metrics/metric-card";
import { usd, ms, tokens } from "@/lib/format";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

interface DiagnosticsCardsProps {
  diagnostics: DiagnosticsSummary;
}

export function DiagnosticsCards({ diagnostics }: DiagnosticsCardsProps) {
  const modelData = Object.entries(diagnostics.by_model ?? {}).map(([key, m]) => ({
    model: key,
    calls: m.calls,
    input_tokens: m.input_tokens,
    output_tokens: m.output_tokens,
    cost: m.cost_usd,
    avg_latency: m.avg_latency_ms,
  }));

  return (
    <div className="space-y-6">
      {/* Summary cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <MetricCard label="Total Cost" value={usd(diagnostics.total_cost_usd)} />
        <MetricCard label="Total Tokens" value={tokens(diagnostics.total_tokens)} sublabel={`${tokens(diagnostics.total_input_tokens)} in / ${tokens(diagnostics.total_output_tokens)} out`} />
        <MetricCard label="Avg Latency" value={ms(diagnostics.avg_latency_ms)} sublabel={`min: ${ms(diagnostics.min_latency_ms)} / max: ${ms(diagnostics.max_latency_ms)}`} />
        <MetricCard label="Success Rate" value={`${(diagnostics.success_rate * 100).toFixed(0)}%`} sublabel={`${diagnostics.successful_calls}/${diagnostics.total_calls} calls`} />
      </div>

      {/* Latency chart */}
      {modelData.length > 0 && (
        <div>
          <h3 className="text-sm font-medium mb-2">Latency by Model</h3>
          <div className="h-52">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={modelData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="model" fontSize={11} />
                <YAxis fontSize={11} tickFormatter={(v) => `${v}ms`} />
                <Tooltip formatter={(v) => `${Number(v).toFixed(0)}ms`} />
                <Bar dataKey="avg_latency" fill="#8b5cf6" name="Avg Latency (ms)" radius={[2, 2, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* Token usage chart */}
      {modelData.length > 0 && (
        <div>
          <h3 className="text-sm font-medium mb-2">Token Usage by Model</h3>
          <div className="h-52">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={modelData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="model" fontSize={11} />
                <YAxis fontSize={11} tickFormatter={(v) => tokens(v)} />
                <Tooltip formatter={(v) => tokens(Number(v))} />
                <Bar dataKey="input_tokens" fill="#3b82f6" name="Input" stackId="tokens" radius={[0, 0, 0, 0]} />
                <Bar dataKey="output_tokens" fill="#06b6d4" name="Output" stackId="tokens" radius={[2, 2, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}
    </div>
  );
}
