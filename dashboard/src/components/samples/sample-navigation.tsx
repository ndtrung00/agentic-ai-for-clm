"use client";

import Link from "next/link";
import type { SampleSummary } from "@/lib/types";

interface SampleNavigationProps {
  samples: SampleSummary[];
  currentSampleId: string;
  runId: string;
}

export function SampleNavigation({ samples, currentSampleId, runId }: SampleNavigationProps) {
  const currentIdx = samples.findIndex((s) => s.id === currentSampleId);
  if (currentIdx === -1) return null;

  const prevSample = currentIdx > 0 ? samples[currentIdx - 1] : null;
  const nextSample = currentIdx < samples.length - 1 ? samples[currentIdx + 1] : null;

  // Find next FP or FN sample
  const nextErrorIdx = samples.findIndex(
    (s, i) => i > currentIdx && (s.classification === "FP" || s.classification === "FN"),
  );
  const nextErrorSample = nextErrorIdx >= 0 ? samples[nextErrorIdx] : null;

  const sampleUrl = (sampleId: string) =>
    `/experiments/${encodeURIComponent(runId)}/samples/${encodeURIComponent(sampleId)}`;

  return (
    <div className="flex items-center justify-between border rounded-md p-2 bg-muted/30">
      <div className="flex items-center gap-2">
        {prevSample ? (
          <Link
            href={sampleUrl(prevSample.id)}
            className="px-3 py-1.5 text-xs font-medium rounded-md border bg-background hover:bg-muted transition-colors"
          >
            &larr; Prev
          </Link>
        ) : (
          <span className="px-3 py-1.5 text-xs font-medium rounded-md border opacity-40">
            &larr; Prev
          </span>
        )}

        {nextSample ? (
          <Link
            href={sampleUrl(nextSample.id)}
            className="px-3 py-1.5 text-xs font-medium rounded-md border bg-background hover:bg-muted transition-colors"
          >
            Next &rarr;
          </Link>
        ) : (
          <span className="px-3 py-1.5 text-xs font-medium rounded-md border opacity-40">
            Next &rarr;
          </span>
        )}
      </div>

      <span className="text-xs text-muted-foreground">
        Sample {currentIdx + 1} of {samples.length}
      </span>

      <div>
        {nextErrorSample ? (
          <Link
            href={sampleUrl(nextErrorSample.id)}
            className="px-3 py-1.5 text-xs font-medium rounded-md border border-red-200 bg-red-50 text-red-700 hover:bg-red-100 transition-colors"
          >
            Next FP/FN &rarr;
          </Link>
        ) : (
          <span className="px-3 py-1.5 text-xs font-medium rounded-md border opacity-40">
            No more FP/FN
          </span>
        )}
      </div>
    </div>
  );
}
