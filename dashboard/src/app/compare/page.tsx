import { listExperiments, getExperiment } from "@/lib/data-loader";
import { ComparisonView } from "./comparison-view";

export const dynamic = "force-dynamic";

interface Props {
  searchParams: Promise<{ runs?: string }>;
}

export default async function ComparePage({ searchParams }: Props) {
  const { runs: runsParam } = await searchParams;
  const allExperiments = listExperiments();

  // Parse selected run IDs from query params
  const selectedIds = runsParam
    ? runsParam.split(",").map((r) => r.trim()).filter(Boolean).slice(0, 4)
    : [];

  // Load full experiment data for selected runs
  const selectedExperiments = selectedIds
    .map((id) => getExperiment(id))
    .filter((e) => e !== null);

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Compare Experiments</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Select up to 4 experiments to compare side-by-side.
        </p>
      </div>

      <ComparisonView
        allExperiments={allExperiments}
        initialExperiments={selectedExperiments}
        initialIds={selectedIds}
      />
    </div>
  );
}
