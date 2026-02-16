"use client";

import { useState } from "react";
import type { ExperimentSummary } from "@/lib/types";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { MetricsGrid } from "@/components/metrics/metrics-grid";
import { ConfusionMatrix } from "@/components/metrics/confusion-matrix";
import { TierBreakdown } from "@/components/metrics/tier-breakdown";
import { ClassificationPie } from "@/components/charts/classification-pie";
import { SamplesTable } from "@/components/samples/samples-table";
import { DiagnosticsCards } from "@/components/diagnostics/diagnostics-cards";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

interface ExperimentTabsProps {
  experiment: ExperimentSummary;
  runId: string;
}

export function ExperimentTabs({ experiment, runId }: ExperimentTabsProps) {
  const hasConfig = !!(experiment.prompt || experiment.architecture);

  return (
    <Tabs defaultValue="overview">
      <TabsList>
        <TabsTrigger value="overview">Overview</TabsTrigger>
        <TabsTrigger value="samples">Samples ({experiment.samples.length})</TabsTrigger>
        {experiment.diagnostics && <TabsTrigger value="diagnostics">Diagnostics</TabsTrigger>}
        {hasConfig && <TabsTrigger value="config">Config</TabsTrigger>}
      </TabsList>

      {/* Overview Tab */}
      <TabsContent value="overview" className="space-y-6">
        <MetricsGrid metrics={experiment.metrics} />

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <ConfusionMatrix metrics={experiment.metrics} />
          <ClassificationPie metrics={experiment.metrics} />
        </div>

        {Object.keys(experiment.per_tier).length > 0 && (
          <TierBreakdown perTier={experiment.per_tier} />
        )}
      </TabsContent>

      {/* Samples Tab */}
      <TabsContent value="samples">
        <SamplesTable samples={experiment.samples} runId={runId} />
      </TabsContent>

      {/* Diagnostics Tab */}
      {experiment.diagnostics && (
        <TabsContent value="diagnostics">
          <DiagnosticsCards diagnostics={experiment.diagnostics} />
        </TabsContent>
      )}

      {/* Config Tab */}
      {hasConfig && (
        <TabsContent value="config" className="space-y-4">
          {/* Architecture (multi-agent runs) */}
          {experiment.architecture && (
            <ArchitectureSection architecture={experiment.architecture} />
          )}

          {/* System Prompt (baseline runs) */}
          {experiment.prompt && (
            <Card>
              <CardHeader>
                <CardTitle className="text-sm">System Prompt</CardTitle>
              </CardHeader>
              <CardContent>
                <pre className="text-sm whitespace-pre-wrap bg-muted p-4 rounded-md">
                  {experiment.prompt.system_prompt}
                </pre>
              </CardContent>
            </Card>
          )}

          {/* Model Configuration */}
          <Card>
            <CardHeader>
              <CardTitle className="text-sm">Model Configuration</CardTitle>
            </CardHeader>
            <CardContent>
              <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
                <dt className="text-muted-foreground">Model ID</dt>
                <dd className="font-mono">{experiment.config.model_id}</dd>
                <dt className="text-muted-foreground">Temperature</dt>
                <dd>{experiment.config.temperature}</dd>
                <dt className="text-muted-foreground">Max Tokens</dt>
                <dd>{experiment.config.max_tokens}</dd>
                <dt className="text-muted-foreground">Samples per Tier</dt>
                <dd>{experiment.config.samples_per_tier}</dd>
                {experiment.config.max_contract_chars && (
                  <>
                    <dt className="text-muted-foreground">Max Contract Chars</dt>
                    <dd>{experiment.config.max_contract_chars.toLocaleString()}</dd>
                  </>
                )}
              </dl>
            </CardContent>
          </Card>
        </TabsContent>
      )}
    </Tabs>
  );
}

function ArchitectureSection({ architecture }: { architecture: NonNullable<ExperimentSummary["architecture"]> }) {
  const [expandedSpecialist, setExpandedSpecialist] = useState<string | null>(null);

  return (
    <>
      {/* Architecture Overview */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Architecture</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <p className="text-sm">{architecture.description}</p>

          <div className="flex items-center gap-1 text-sm">
            <span className="text-muted-foreground">Workflow:</span>
            {architecture.workflow.map((step, i) => (
              <span key={step} className="flex items-center gap-1">
                {i > 0 && <span className="text-muted-foreground">&rarr;</span>}
                <Badge variant="outline">{step}</Badge>
              </span>
            ))}
          </div>

          {architecture.validation_enabled !== undefined && (
            <div className="text-sm">
              <span className="text-muted-foreground">Validation: </span>
              <span>{architecture.validation_enabled ? "Enabled" : "Disabled"}</span>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Specialist Prompts (M1) */}
      {architecture.specialist_prompts && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">
              Specialist Agents ({Object.keys(architecture.specialist_prompts).length})
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {Object.entries(architecture.specialist_prompts).map(([name, info]) => (
              <details
                key={name}
                open={expandedSpecialist === name}
                onToggle={(e) => {
                  const target = e.target as HTMLDetailsElement;
                  setExpandedSpecialist(target.open ? name : null);
                }}
                className="border rounded-lg"
              >
                <summary className="cursor-pointer p-3 text-sm font-medium flex items-center justify-between">
                  <span>{name}</span>
                  <span className="flex items-center gap-2">
                    <Badge variant="secondary">{info.category_count} categories</Badge>
                    <Badge variant="outline">v{info.version}</Badge>
                  </span>
                </summary>
                <div className="px-3 pb-3 space-y-2">
                  <p className="text-xs text-muted-foreground">{info.description}</p>
                  <div className="text-xs">
                    <span className="text-muted-foreground">Categories: </span>
                    {info.categories.join(", ")}
                  </div>
                  <pre className="text-xs whitespace-pre-wrap bg-muted p-3 rounded-md max-h-60 overflow-y-auto">
                    {info.system_prompt}
                  </pre>
                </div>
              </details>
            ))}
          </CardContent>
        </Card>
      )}

      {/* Category Routing Table (M1) */}
      {architecture.routing_table && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">
              Category Routing ({Object.keys(architecture.routing_table).length} categories)
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-1 text-sm">
              {Object.entries(architecture.routing_table).map(([category, specialist]) => (
                <div key={category} className="flex justify-between">
                  <span>{category}</span>
                  <Badge variant="outline" className="text-xs">{specialist}</Badge>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Combined Prompt (M6) */}
      {architecture.system_prompt && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Combined Prompt Template</CardTitle>
          </CardHeader>
          <CardContent>
            <pre className="text-sm whitespace-pre-wrap bg-muted p-4 rounded-md max-h-96 overflow-y-auto">
              {architecture.system_prompt}
            </pre>
          </CardContent>
        </Card>
      )}
    </>
  );
}
