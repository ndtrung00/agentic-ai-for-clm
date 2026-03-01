"use client";

import { useState, useMemo } from "react";
import { useRouter } from "next/navigation";
import type { ExperimentListItem, ExperimentSummary } from "@/lib/types";
import { RunSelector } from "@/components/comparison/run-selector";
import { MetricsComparison } from "@/components/comparison/metrics-comparison";
import { TierComparison } from "@/components/comparison/tier-comparison";
import { CategoryComparison } from "@/components/comparison/category-comparison";
import { SampleDiff } from "@/components/comparison/sample-diff";
import { StatisticalSummary } from "@/components/comparison/statistical-summary";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

interface ComparisonViewProps {
  allExperiments: ExperimentListItem[];
  initialExperiments: ExperimentSummary[];
  initialIds: string[];
}

export function ComparisonView({
  allExperiments,
  initialExperiments,
  initialIds,
}: ComparisonViewProps) {
  const router = useRouter();
  const [selectedIds, setSelectedIds] = useState<string[]>(initialIds);
  const experiments = initialExperiments;

  const handleSelectionChange = (ids: string[]) => {
    setSelectedIds(ids);
    const params = new URLSearchParams();
    if (ids.length > 0) params.set("runs", ids.join(","));
    router.push(`/compare?${params.toString()}`);
  };

  const hasComparison = experiments.length >= 2;

  return (
    <div className="space-y-6">
      <RunSelector
        allExperiments={allExperiments}
        selectedIds={selectedIds}
        onSelectionChange={handleSelectionChange}
        maxSelections={4}
      />

      {experiments.length === 0 && (
        <p className="text-center text-muted-foreground py-12">
          Select experiments above to begin comparison.
        </p>
      )}

      {experiments.length === 1 && (
        <p className="text-center text-muted-foreground py-12">
          Select at least one more experiment to compare.
        </p>
      )}

      {hasComparison && (
        <Tabs defaultValue="metrics">
          <TabsList>
            <TabsTrigger value="metrics">Metrics</TabsTrigger>
            <TabsTrigger value="tiers">Tier Comparison</TabsTrigger>
            <TabsTrigger value="categories">Category Heatmap</TabsTrigger>
            <TabsTrigger value="samples">Sample Diffs</TabsTrigger>
          </TabsList>

          <TabsContent value="metrics" className="space-y-6">
            <StatisticalSummary experiments={experiments} />
            <MetricsComparison experiments={experiments} />
          </TabsContent>

          <TabsContent value="tiers" className="space-y-6">
            <TierComparison experiments={experiments} />
          </TabsContent>

          <TabsContent value="categories" className="space-y-6">
            <CategoryComparison experiments={experiments} />
          </TabsContent>

          <TabsContent value="samples" className="space-y-6">
            <SampleDiff experiments={experiments} />
          </TabsContent>
        </Tabs>
      )}
    </div>
  );
}
