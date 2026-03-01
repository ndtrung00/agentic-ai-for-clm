"use client";

import { useMemo, useState } from "react";
import type { ExperimentListItem } from "@/lib/types";
import { formatDate, fixed, pct } from "@/lib/format";
import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

interface RunSelectorProps {
  allExperiments: ExperimentListItem[];
  selectedIds: string[];
  onSelectionChange: (ids: string[]) => void;
  maxSelections: number;
}

// Stable color palette for distinguishing runs
export const RUN_COLORS = ["#3b82f6", "#f97316", "#22c55e", "#a855f7"];

export function runLabel(exp: ExperimentListItem | { config: { baseline_type: string; model_key: string } }): string {
  if ("config" in exp) {
    return `${exp.config.baseline_type} / ${exp.config.model_key}`;
  }
  return `${exp.baseline_type} / ${exp.model_key}`;
}

type ViewMode = "cards" | "table";

export function RunSelector({
  allExperiments,
  selectedIds,
  onSelectionChange,
  maxSelections,
}: RunSelectorProps) {
  const selectedSet = useMemo(() => new Set(selectedIds), [selectedIds]);
  const [viewMode, setViewMode] = useState<ViewMode>("table");

  const toggle = (runId: string) => {
    if (selectedSet.has(runId)) {
      onSelectionChange(selectedIds.filter((id) => id !== runId));
    } else if (selectedIds.length < maxSelections) {
      onSelectionChange([...selectedIds, runId]);
    }
  };

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-medium">
          Select Experiments ({selectedIds.length}/{maxSelections})
        </h3>
        <div className="flex items-center gap-3">
          {selectedIds.length > 0 && (
            <button
              onClick={() => onSelectionChange([])}
              className="text-sm text-muted-foreground hover:text-foreground underline underline-offset-2"
            >
              Clear all
            </button>
          )}
          <div className="inline-flex rounded-md border border-input bg-background">
            <button
              onClick={() => setViewMode("table")}
              className={`px-2.5 py-1 text-sm rounded-l-md transition-colors ${
                viewMode === "table"
                  ? "bg-primary text-primary-foreground"
                  : "hover:bg-muted"
              }`}
              title="Table view"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 10h18M3 14h18M3 6h18M3 18h18" />
              </svg>
            </button>
            <button
              onClick={() => setViewMode("cards")}
              className={`px-2.5 py-1 text-sm rounded-r-md transition-colors ${
                viewMode === "cards"
                  ? "bg-primary text-primary-foreground"
                  : "hover:bg-muted"
              }`}
              title="Card view"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zm10 0a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zm10 0a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z" />
              </svg>
            </button>
          </div>
        </div>
      </div>

      {viewMode === "cards" ? (
        <CardView
          experiments={allExperiments}
          selectedIds={selectedIds}
          selectedSet={selectedSet}
          maxSelections={maxSelections}
          toggle={toggle}
        />
      ) : (
        <TableView
          experiments={allExperiments}
          selectedIds={selectedIds}
          selectedSet={selectedSet}
          maxSelections={maxSelections}
          toggle={toggle}
        />
      )}
    </div>
  );
}

// ── Card View (original) ──────────────────────────────────────────────────

function CardView({
  experiments,
  selectedIds,
  selectedSet,
  maxSelections,
  toggle,
}: {
  experiments: ExperimentListItem[];
  selectedIds: string[];
  selectedSet: Set<string>;
  maxSelections: number;
  toggle: (id: string) => void;
}) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-2 max-h-64 overflow-y-auto border rounded-md p-2">
      {experiments.map((exp) => {
        const isSelected = selectedSet.has(exp.run_id);
        const colorIdx = selectedIds.indexOf(exp.run_id);
        const atMax = selectedIds.length >= maxSelections && !isSelected;
        return (
          <label
            key={exp.run_id}
            className={`flex items-center gap-3 p-2 rounded-md cursor-pointer transition-colors ${
              isSelected ? "bg-muted" : atMax ? "opacity-50" : "hover:bg-muted/50"
            }`}
          >
            <Checkbox
              checked={isSelected}
              onCheckedChange={() => toggle(exp.run_id)}
              disabled={atMax}
            />
            {isSelected && colorIdx >= 0 && (
              <span
                className="w-3 h-3 rounded-full flex-shrink-0"
                style={{ backgroundColor: RUN_COLORS[colorIdx] }}
              />
            )}
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium truncate">{exp.model_key}</span>
                <Badge variant="secondary" className="text-xs">{exp.baseline_type}</Badge>
              </div>
              <div className="text-xs text-muted-foreground flex gap-3">
                <span>{exp.provider}</span>
                <span>F2: {fixed(exp.f2)}</span>
                <span>{formatDate(exp.timestamp)}</span>
              </div>
            </div>
          </label>
        );
      })}
    </div>
  );
}

// ── Table View ────────────────────────────────────────────────────────────

function TableView({
  experiments,
  selectedIds,
  selectedSet,
  maxSelections,
  toggle,
}: {
  experiments: ExperimentListItem[];
  selectedIds: string[];
  selectedSet: Set<string>;
  maxSelections: number;
  toggle: (id: string) => void;
}) {
  return (
    <div className="border rounded-md max-h-80 overflow-y-auto">
      <Table>
        <TableHeader className="sticky top-0 bg-background z-10">
          <TableRow>
            <TableHead className="w-10"></TableHead>
            <TableHead>Model</TableHead>
            <TableHead>Config</TableHead>
            <TableHead>Provider</TableHead>
            <TableHead className="text-right">F2</TableHead>
            <TableHead className="text-right">F1</TableHead>
            <TableHead className="text-right">Jaccard</TableHead>
            <TableHead className="text-right">Laziness</TableHead>
            <TableHead className="text-right">Samples</TableHead>
            <TableHead>Date</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {experiments.map((exp) => {
            const isSelected = selectedSet.has(exp.run_id);
            const colorIdx = selectedIds.indexOf(exp.run_id);
            const atMax = selectedIds.length >= maxSelections && !isSelected;
            return (
              <TableRow
                key={exp.run_id}
                className={`cursor-pointer transition-colors ${
                  isSelected ? "bg-muted" : atMax ? "opacity-50" : "hover:bg-muted/50"
                }`}
                onClick={() => {
                  if (!atMax) toggle(exp.run_id);
                }}
              >
                <TableCell className="w-10" onClick={(e) => e.stopPropagation()}>
                  <div className="flex items-center gap-1.5">
                    <Checkbox
                      checked={isSelected}
                      onCheckedChange={() => toggle(exp.run_id)}
                      disabled={atMax}
                    />
                    {isSelected && colorIdx >= 0 && (
                      <span
                        className="w-2.5 h-2.5 rounded-full flex-shrink-0"
                        style={{ backgroundColor: RUN_COLORS[colorIdx] }}
                      />
                    )}
                  </div>
                </TableCell>
                <TableCell className="font-medium text-sm">{exp.model_key}</TableCell>
                <TableCell>
                  <Badge variant="secondary" className="text-xs">{exp.baseline_type}</Badge>
                </TableCell>
                <TableCell className="text-sm text-muted-foreground">{exp.provider}</TableCell>
                <TableCell className="text-right font-mono font-medium text-sm">{fixed(exp.f2)}</TableCell>
                <TableCell className="text-right font-mono text-sm">{fixed(exp.f1)}</TableCell>
                <TableCell className="text-right font-mono text-sm">{fixed(exp.avg_jaccard)}</TableCell>
                <TableCell className="text-right font-mono text-sm">{pct(exp.laziness_rate)}</TableCell>
                <TableCell className="text-right text-sm">{exp.sample_count}</TableCell>
                <TableCell className="text-sm text-muted-foreground">{formatDate(exp.timestamp)}</TableCell>
              </TableRow>
            );
          })}
          {experiments.length === 0 && (
            <TableRow>
              <TableCell colSpan={10} className="text-center text-muted-foreground py-8">
                No experiments available.
              </TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>
    </div>
  );
}
