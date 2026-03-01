"use client";

import { downloadCSV, downloadJSON } from "@/lib/export";

interface ExportButtonProps {
  data: Record<string, unknown>[];
  filename: string;
  columns?: string[];
  label?: string;
  format?: "csv" | "json";
}

export function ExportButton({
  data,
  filename,
  columns,
  label = "Export CSV",
  format = "csv",
}: ExportButtonProps) {
  const handleExport = () => {
    if (format === "json") {
      downloadJSON(data, filename);
    } else {
      downloadCSV(data, filename, columns);
    }
  };

  return (
    <button
      onClick={handleExport}
      className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md border border-input bg-background hover:bg-muted transition-colors"
    >
      <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
      </svg>
      {label}
    </button>
  );
}
