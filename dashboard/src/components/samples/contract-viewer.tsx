import type { SampleDetail } from "@/lib/types";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ClassificationBadge } from "./classification-badge";

interface ContractViewerProps {
  sample: SampleDetail;
}

export function ContractViewer({ sample }: ContractViewerProps) {
  const gtSpans = sample.ground_truth.spans.filter((s) => s.trim());
  const predicted = sample.output.parsed_clauses.filter((c) => c.trim());
  const isNoClause = predicted.length === 0 ||
    predicted.every((c) => c.toLowerCase().includes("no related clause"));

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      {/* Ground Truth */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm flex items-center gap-2">
            Ground Truth
            <span className="text-xs text-muted-foreground font-normal">
              {gtSpans.length} span{gtSpans.length !== 1 ? "s" : ""}
            </span>
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          {gtSpans.length === 0 ? (
            <p className="text-sm text-muted-foreground italic">No ground truth clause</p>
          ) : (
            gtSpans.map((span, i) => (
              <div
                key={i}
                className="p-3 rounded-md bg-yellow-50 border border-yellow-200 text-sm leading-relaxed whitespace-pre-wrap"
              >
                {span}
              </div>
            ))
          )}
        </CardContent>
      </Card>

      {/* Prediction */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm flex items-center gap-2">
            Prediction
            <ClassificationBadge value={sample.evaluation.classification} />
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          {isNoClause ? (
            <p className="text-sm text-muted-foreground italic">
              Model predicted &quot;No related clause&quot;
            </p>
          ) : (
            predicted.map((clause, i) => {
              // Check if this clause appears in any GT span
              const matchesGT = gtSpans.some(
                (gt) => gt.toLowerCase().includes(clause.toLowerCase().slice(0, 50)) ||
                  clause.toLowerCase().includes(gt.toLowerCase().slice(0, 50))
              );
              return (
                <div
                  key={i}
                  className={`p-3 rounded-md text-sm leading-relaxed whitespace-pre-wrap ${
                    matchesGT
                      ? "bg-green-50 border border-green-200"
                      : "bg-gray-50 border border-gray-200"
                  }`}
                >
                  {clause}
                </div>
              );
            })
          )}
        </CardContent>
      </Card>
    </div>
  );
}
