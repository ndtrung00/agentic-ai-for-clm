import { listExperiments } from "@/lib/data-loader";
import { ExperimentsTable } from "./experiments-table";
import { RefreshButton } from "@/components/ui/refresh-button";

export const dynamic = "force-dynamic";

export default function ExperimentsPage() {
  const experiments = listExperiments();

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold">Experiments</h1>
          <p className="text-sm text-muted-foreground mt-1">
            {experiments.length} experiment run{experiments.length !== 1 ? "s" : ""} found
          </p>
        </div>
        <RefreshButton />
      </div>

      <ExperimentsTable experiments={experiments} />
    </div>
  );
}
