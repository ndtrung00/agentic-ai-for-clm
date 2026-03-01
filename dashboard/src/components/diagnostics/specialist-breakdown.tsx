"use client";

import { useMemo } from "react";
import type { DiagnosticsSummary, SampleSummary } from "@/lib/types";
import { computeCategoryMetrics } from "@/lib/category-utils";
import { usd, ms, tokens, fixed } from "@/lib/format";
import { MetricCard } from "@/components/metrics/metric-card";
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

interface SpecialistBreakdownProps {
  diagnostics: DiagnosticsSummary;
  samples: SampleSummary[];
  routingTable?: Record<string, string>;
}

const SPECIALIST_COLORS: Record<string, string> = {
  risk_liability: "#ef4444",
  temporal_renewal: "#3b82f6",
  ip_commercial: "#22c55e",
  orchestrator: "#8b5cf6",
  validator: "#f59e0b",
};

const SPECIALIST_LABELS: Record<string, string> = {
  risk_liability: "Risk & Liability",
  temporal_renewal: "Temporal/Renewal",
  ip_commercial: "IP & Commercial",
  orchestrator: "Orchestrator",
  validator: "Validator",
};

export function SpecialistBreakdown({ diagnostics, samples, routingTable }: SpecialistBreakdownProps) {
  // Per-specialist performance from sample routing
  const specialistMetrics = useMemo(() => {
    if (!routingTable) return [];

    // Group samples by specialist
    const grouped = new Map<string, SampleSummary[]>();
    for (const s of samples) {
      const specialist = routingTable[s.category];
      if (!specialist) continue;
      const existing = grouped.get(specialist) ?? [];
      existing.push(s);
      grouped.set(specialist, existing);
    }

    return [...grouped.entries()].map(([name, specialistSamples]) => {
      const cats = computeCategoryMetrics(specialistSamples);
      const totalTP = cats.reduce((sum, c) => sum + c.tp, 0);
      const totalFP = cats.reduce((sum, c) => sum + c.fp, 0);
      const totalFN = cats.reduce((sum, c) => sum + c.fn, 0);
      const precision = totalTP + totalFP > 0 ? totalTP / (totalTP + totalFP) : 0;
      const recall = totalTP + totalFN > 0 ? totalTP / (totalTP + totalFN) : 0;
      const f2 = precision + recall > 0 ? (5 * precision * recall) / (4 * precision + recall) : 0;

      return {
        name,
        label: SPECIALIST_LABELS[name] ?? name,
        sampleCount: specialistSamples.length,
        categoryCount: cats.length,
        f2,
        precision,
        recall,
        calls: diagnostics.by_agent?.[name] ?? 0,
      };
    });
  }, [samples, routingTable, diagnostics.by_agent]);

  // Chart data for per-agent calls
  const agentCallData = useMemo(() => {
    if (!diagnostics.by_agent) return [];
    return Object.entries(diagnostics.by_agent).map(([agent, calls]) => ({
      agent: SPECIALIST_LABELS[agent] ?? agent,
      calls,
      color: SPECIALIST_COLORS[agent] ?? "#94a3b8",
    }));
  }, [diagnostics.by_agent]);

  if (specialistMetrics.length === 0 && agentCallData.length === 0) return null;

  return (
    <div className="space-y-6">
      <h3 className="text-sm font-medium">Per-Specialist Breakdown</h3>

      {/* Specialist performance cards */}
      {specialistMetrics.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {specialistMetrics.map((s) => (
            <div
              key={s.name}
              className="border rounded-lg p-4 space-y-2"
              style={{ borderLeftColor: SPECIALIST_COLORS[s.name] ?? "#94a3b8", borderLeftWidth: 3 }}
            >
              <div className="font-medium text-sm">{s.label}</div>
              <div className="text-xs text-muted-foreground">
                {s.categoryCount} categories, {s.sampleCount} samples
              </div>
              <div className="grid grid-cols-3 gap-2 text-xs">
                <div>
                  <div className="text-muted-foreground">F2</div>
                  <div className="font-mono font-medium">{fixed(s.f2)}</div>
                </div>
                <div>
                  <div className="text-muted-foreground">Precision</div>
                  <div className="font-mono">{fixed(s.precision)}</div>
                </div>
                <div>
                  <div className="text-muted-foreground">Recall</div>
                  <div className="font-mono">{fixed(s.recall)}</div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Agent call distribution chart */}
      {agentCallData.length > 0 && (
        <div>
          <h4 className="text-sm font-medium mb-2">Calls by Agent</h4>
          <div className="h-52">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={agentCallData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="agent" fontSize={11} />
                <YAxis fontSize={11} />
                <Tooltip />
                <Bar dataKey="calls" fill="#8b5cf6" name="Calls" radius={[2, 2, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}
    </div>
  );
}
