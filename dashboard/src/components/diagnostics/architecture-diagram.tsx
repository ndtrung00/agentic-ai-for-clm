"use client";

import type { Architecture, DiagnosticsSummary } from "@/lib/types";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

interface ArchitectureDiagramProps {
  architecture: Architecture;
  diagnostics?: DiagnosticsSummary;
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

export function ArchitectureDiagram({ architecture, diagnostics }: ArchitectureDiagramProps) {
  const specialists = architecture.specialists ?? [];
  const byAgent = diagnostics?.by_agent ?? {};

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm">Architecture Diagram</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="flex flex-col items-center gap-3 py-4">
          {/* Orchestrator */}
          <div
            className="border-2 rounded-lg px-6 py-3 text-center min-w-[200px]"
            style={{ borderColor: SPECIALIST_COLORS.orchestrator }}
          >
            <div className="font-medium text-sm">Orchestrator</div>
            <div className="text-xs text-muted-foreground">Routes to specialists</div>
            {byAgent["orchestrator"] != null && (
              <div className="text-xs mt-1 font-mono">{byAgent["orchestrator"]} calls</div>
            )}
          </div>

          {/* Arrows down */}
          <div className="flex items-center gap-8">
            {specialists.map((_, i) => (
              <svg key={i} className="w-4 h-6" viewBox="0 0 16 24">
                <path d="M8 0 L8 18 M4 14 L8 22 L12 14" stroke="currentColor" fill="none" strokeWidth="1.5" className="text-muted-foreground" />
              </svg>
            ))}
          </div>

          {/* Specialist boxes */}
          <div className="flex gap-4 flex-wrap justify-center">
            {specialists.map((name) => {
              const color = SPECIALIST_COLORS[name] ?? "#94a3b8";
              const label = SPECIALIST_LABELS[name] ?? name;
              const catCount = architecture.specialist_prompts?.[name]?.category_count ?? 0;
              const calls = byAgent[name];
              return (
                <div
                  key={name}
                  className="border-2 rounded-lg px-4 py-3 text-center min-w-[160px]"
                  style={{ borderColor: color }}
                >
                  <div className="font-medium text-sm">{label}</div>
                  <div className="text-xs text-muted-foreground">{catCount} categories</div>
                  {calls != null && (
                    <div className="text-xs mt-1 font-mono">{calls} calls</div>
                  )}
                </div>
              );
            })}
          </div>

          {/* Arrows down to validator */}
          {architecture.validation_enabled && (
            <>
              <div className="flex items-center gap-8">
                {specialists.map((_, i) => (
                  <svg key={i} className="w-4 h-6" viewBox="0 0 16 24">
                    <path d="M8 0 L8 18 M4 14 L8 22 L12 14" stroke="currentColor" fill="none" strokeWidth="1.5" className="text-muted-foreground" />
                  </svg>
                ))}
              </div>

              <div
                className="border-2 rounded-lg px-6 py-3 text-center min-w-[200px]"
                style={{ borderColor: SPECIALIST_COLORS.validator }}
              >
                <div className="font-medium text-sm">Validation Layer</div>
                <div className="text-xs text-muted-foreground">Format + grounding check</div>
                {byAgent["validator"] != null && (
                  <div className="text-xs mt-1 font-mono">{byAgent["validator"]} calls</div>
                )}
              </div>
            </>
          )}

          {/* Final output */}
          <svg className="w-4 h-6" viewBox="0 0 16 24">
            <path d="M8 0 L8 18 M4 14 L8 22 L12 14" stroke="currentColor" fill="none" strokeWidth="1.5" className="text-muted-foreground" />
          </svg>

          <div className="border rounded-lg px-6 py-2 text-center bg-muted/50">
            <div className="text-sm font-medium">Output</div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
