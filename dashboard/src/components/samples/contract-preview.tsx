"use client";

import { useMemo } from "react";

interface ContractPreviewProps {
  contractTitle: string;
  contractText: string;
  gtSpans: string[];
  predictedClauses: string[];
}

interface Segment {
  text: string;
  type: "plain" | "gt" | "predicted" | "both";
}

/**
 * Find all non-overlapping occurrences of a substring in text.
 * Returns [start, end) index pairs.
 */
function findAllOccurrences(text: string, needle: string): [number, number][] {
  if (!needle || needle.length < 5) return []; // skip tiny/empty strings
  const results: [number, number][] = [];
  const lowerText = text.toLowerCase();
  const lowerNeedle = needle.toLowerCase().trim();
  if (!lowerNeedle) return results;

  let pos = 0;
  while (pos < lowerText.length) {
    const idx = lowerText.indexOf(lowerNeedle, pos);
    if (idx === -1) break;
    results.push([idx, idx + lowerNeedle.length]);
    pos = idx + lowerNeedle.length;
  }
  return results;
}

/**
 * Merge overlapping intervals. Input: sorted by start.
 */
function mergeIntervals(intervals: [number, number][]): [number, number][] {
  if (intervals.length === 0) return [];
  const sorted = [...intervals].sort((a, b) => a[0] - b[0]);
  const merged: [number, number][] = [sorted[0]];
  for (let i = 1; i < sorted.length; i++) {
    const last = merged[merged.length - 1];
    if (sorted[i][0] <= last[1]) {
      last[1] = Math.max(last[1], sorted[i][1]);
    } else {
      merged.push(sorted[i]);
    }
  }
  return merged;
}

/**
 * Build segments from text with highlight intervals for GT and predicted.
 */
function buildSegments(
  text: string,
  gtIntervals: [number, number][],
  predIntervals: [number, number][]
): Segment[] {
  // Build a sorted list of boundary events
  type Event = { pos: number; type: "gt" | "pred"; start: boolean };
  const events: Event[] = [];
  for (const [s, e] of gtIntervals) {
    events.push({ pos: s, type: "gt", start: true });
    events.push({ pos: e, type: "gt", start: false });
  }
  for (const [s, e] of predIntervals) {
    events.push({ pos: s, type: "pred", start: true });
    events.push({ pos: e, type: "pred", start: false });
  }
  events.sort((a, b) => a.pos - b.pos || (a.start ? 0 : 1) - (b.start ? 0 : 1));

  const segments: Segment[] = [];
  let cursor = 0;
  let inGt = 0;
  let inPred = 0;

  function segType(): Segment["type"] {
    if (inGt > 0 && inPred > 0) return "both";
    if (inGt > 0) return "gt";
    if (inPred > 0) return "predicted";
    return "plain";
  }

  for (const ev of events) {
    if (ev.pos > cursor) {
      segments.push({ text: text.slice(cursor, ev.pos), type: segType() });
      cursor = ev.pos;
    }
    if (ev.type === "gt") inGt += ev.start ? 1 : -1;
    else inPred += ev.start ? 1 : -1;
  }
  if (cursor < text.length) {
    segments.push({ text: text.slice(cursor), type: segType() });
  }
  return segments;
}

const STYLE_MAP: Record<Segment["type"], string> = {
  plain: "",
  gt: "bg-yellow-200/70",
  predicted: "bg-green-200/70",
  both: "bg-amber-300/70",
};

export function ContractPreview({
  contractTitle,
  contractText,
  gtSpans,
  predictedClauses,
}: ContractPreviewProps) {
  const charCount = contractText.length;

  const segments = useMemo(() => {
    // Collect all highlight intervals
    let gtAll: [number, number][] = [];
    for (const span of gtSpans) {
      gtAll = gtAll.concat(findAllOccurrences(contractText, span));
    }
    gtAll = mergeIntervals(gtAll);

    let predAll: [number, number][] = [];
    for (const clause of predictedClauses) {
      // Skip "no related clause" predictions
      if (clause.toLowerCase().includes("no related clause")) continue;
      predAll = predAll.concat(findAllOccurrences(contractText, clause));
    }
    predAll = mergeIntervals(predAll);

    if (gtAll.length === 0 && predAll.length === 0) return null;
    return buildSegments(contractText, gtAll, predAll);
  }, [contractText, gtSpans, predictedClauses]);

  return (
    <details className="border rounded-lg">
      <summary className="cursor-pointer p-4 text-sm font-medium flex items-center gap-2">
        <span>Contract Text</span>
        <span className="text-xs text-muted-foreground font-normal">
          {contractTitle} &middot; {charCount.toLocaleString()} chars
        </span>
      </summary>
      <div className="px-4 pb-4 space-y-2">
        {/* Legend */}
        <div className="flex items-center gap-4 text-xs text-muted-foreground">
          <span className="flex items-center gap-1">
            <span className="inline-block w-3 h-3 rounded bg-yellow-200/70 border border-yellow-300" />
            Ground Truth
          </span>
          <span className="flex items-center gap-1">
            <span className="inline-block w-3 h-3 rounded bg-green-200/70 border border-green-300" />
            Prediction
          </span>
          <span className="flex items-center gap-1">
            <span className="inline-block w-3 h-3 rounded bg-amber-300/70 border border-amber-400" />
            Both
          </span>
        </div>

        {/* Contract text with highlights */}
        <div className="max-h-[500px] overflow-y-auto rounded-md border bg-muted/30 p-4">
          <pre className="text-xs whitespace-pre-wrap font-mono leading-relaxed">
            {segments
              ? segments.map((seg, i) =>
                  seg.type === "plain" ? (
                    seg.text
                  ) : (
                    <mark key={i} className={`${STYLE_MAP[seg.type]} rounded px-0.5`}>
                      {seg.text}
                    </mark>
                  )
                )
              : contractText}
          </pre>
        </div>
      </div>
    </details>
  );
}
