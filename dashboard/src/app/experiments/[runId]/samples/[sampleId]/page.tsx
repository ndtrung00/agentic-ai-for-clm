import { notFound } from "next/navigation";
import Link from "next/link";
import { getExperiment, getSamples } from "@/lib/data-loader";
import { fixed, tokens, ms } from "@/lib/format";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ClassificationBadge, TierBadge } from "@/components/samples/classification-badge";
import { ContractViewer } from "@/components/samples/contract-viewer";
import { Separator } from "@/components/ui/separator";

export const dynamic = "force-dynamic";

interface Props {
  params: Promise<{ runId: string; sampleId: string }>;
}

export default async function SampleDetailPage({ params }: Props) {
  const { runId, sampleId } = await params;
  const decoded = decodeURIComponent(sampleId);

  const experiment = getExperiment(runId);
  if (!experiment) return notFound();

  const samples = getSamples(runId);
  const sample = samples.find((s) => s.sample_id === decoded);
  if (!sample) return notFound();

  return (
    <div className="p-6 space-y-6">
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        <Link href="/experiments" className="hover:underline">Experiments</Link>
        <span>/</span>
        <Link href={`/experiments/${encodeURIComponent(runId)}`} className="hover:underline">
          {experiment.config.model_key}
        </Link>
        <span>/</span>
        <span>Sample</span>
      </div>

      {/* Metadata bar */}
      <div className="flex flex-wrap items-center gap-3">
        <h1 className="text-lg font-bold">{sample.category}</h1>
        <TierBadge value={sample.tier} />
        <ClassificationBadge value={sample.evaluation.classification} />
        <Badge variant="outline">Jaccard: {fixed(sample.evaluation.jaccard)}</Badge>
        {sample.evaluation.grounding_rate != null && (
          <Badge variant="outline">Grounding: {fixed(sample.evaluation.grounding_rate)}</Badge>
        )}
        {sample.contract_title && (
          <span className="text-sm text-muted-foreground">
            Contract: {sample.contract_title}
          </span>
        )}
      </div>

      <Separator />

      {/* Side-by-side GT vs Prediction */}
      <ContractViewer sample={sample} />

      {/* Raw response (collapsible) */}
      <details className="border rounded-lg">
        <summary className="cursor-pointer p-4 text-sm font-medium">
          Raw Model Response
        </summary>
        <div className="px-4 pb-4">
          <pre className="text-xs whitespace-pre-wrap bg-muted p-4 rounded-md max-h-96 overflow-y-auto">
            {sample.output.raw_response}
          </pre>
        </div>
      </details>

      {/* Usage details */}
      {sample.usage && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Usage Details</CardTitle>
          </CardHeader>
          <CardContent>
            <dl className="grid grid-cols-2 md:grid-cols-4 gap-x-4 gap-y-2 text-sm">
              <dt className="text-muted-foreground">Input Tokens</dt>
              <dd>{tokens(sample.usage.input_tokens)}</dd>
              <dt className="text-muted-foreground">Output Tokens</dt>
              <dd>{tokens(sample.usage.output_tokens)}</dd>
              <dt className="text-muted-foreground">Latency</dt>
              <dd>{ms(sample.usage.latency_s * 1000)}</dd>
              {sample.usage.cache_read_tokens != null && (
                <>
                  <dt className="text-muted-foreground">Cache Read</dt>
                  <dd>{tokens(sample.usage.cache_read_tokens)}</dd>
                </>
              )}
            </dl>
          </CardContent>
        </Card>
      )}

      {/* Question asked */}
      {sample.input.question && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Question</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm">{sample.input.question}</p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
