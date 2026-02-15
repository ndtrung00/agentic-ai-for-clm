import { notFound } from "next/navigation";
import Link from "next/link";
import { getExperiment } from "@/lib/data-loader";
import { formatDate } from "@/lib/format";
import { Badge } from "@/components/ui/badge";
import { ExperimentTabs } from "./tabs";

export const dynamic = "force-dynamic";

interface Props {
  params: Promise<{ runId: string }>;
}

export default async function ExperimentDetailPage({ params }: Props) {
  const { runId } = await params;
  const experiment = getExperiment(runId);

  if (!experiment) return notFound();

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-2 text-sm text-muted-foreground mb-1">
            <Link href="/experiments" className="hover:underline">Experiments</Link>
            <span>/</span>
            <span>{experiment.config.model_key}</span>
          </div>
          <h1 className="text-2xl font-bold">{experiment.config.model_key}</h1>
          <div className="flex items-center gap-2 mt-1">
            <Badge variant="secondary">{experiment.config.baseline_type}</Badge>
            <Badge variant="outline">{experiment.config.provider}</Badge>
            {experiment.timestamp && (
              <span className="text-sm text-muted-foreground">{formatDate(experiment.timestamp)}</span>
            )}
            <Badge variant="outline" className="ml-2">{experiment.format} format</Badge>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <ExperimentTabs experiment={experiment} runId={runId} />
    </div>
  );
}
