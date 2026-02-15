"use client";

import type { ExperimentSummary } from "@/lib/types";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { MetricsGrid } from "@/components/metrics/metrics-grid";
import { ConfusionMatrix } from "@/components/metrics/confusion-matrix";
import { TierBreakdown } from "@/components/metrics/tier-breakdown";
import { ClassificationPie } from "@/components/charts/classification-pie";
import { SamplesTable } from "@/components/samples/samples-table";
import { DiagnosticsCards } from "@/components/diagnostics/diagnostics-cards";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

interface ExperimentTabsProps {
  experiment: ExperimentSummary;
  runId: string;
}

export function ExperimentTabs({ experiment, runId }: ExperimentTabsProps) {
  return (
    <Tabs defaultValue="overview">
      <TabsList>
        <TabsTrigger value="overview">Overview</TabsTrigger>
        <TabsTrigger value="samples">Samples ({experiment.samples.length})</TabsTrigger>
        {experiment.diagnostics && <TabsTrigger value="diagnostics">Diagnostics</TabsTrigger>}
        {experiment.prompt && <TabsTrigger value="config">Config</TabsTrigger>}
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
      {experiment.prompt && (
        <TabsContent value="config" className="space-y-4">
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
