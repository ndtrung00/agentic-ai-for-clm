"use client";

import { useMemo } from "react";
import type { ExperimentListItem } from "@/lib/types";
import { formatDate, fixed } from "@/lib/format";
import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";

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

export function RunSelector({
  allExperiments,
  selectedIds,
  onSelectionChange,
  maxSelections,
}: RunSelectorProps) {
  const selectedSet = useMemo(() => new Set(selectedIds), [selectedIds]);

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
        {selectedIds.length > 0 && (
          <button
            onClick={() => onSelectionChange([])}
            className="text-sm text-muted-foreground hover:text-foreground underline underline-offset-2"
          >
            Clear all
          </button>
        )}
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-2 max-h-64 overflow-y-auto border rounded-md p-2">
        {allExperiments.map((exp) => {
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
    </div>
  );
}
