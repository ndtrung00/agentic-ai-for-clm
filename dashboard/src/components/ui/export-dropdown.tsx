"use client";

import { useState, useRef, useEffect } from "react";
import { downloadCSV, downloadXLSX } from "@/lib/export";

interface ExportDropdownProps {
  data: Record<string, unknown>[];
  filename: string;
  columns?: string[];
  label?: string;
}

export function ExportDropdown({
  data,
  filename,
  columns,
  label = "Export",
}: ExportDropdownProps) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleCSV = () => {
    downloadCSV(data, filename, columns);
    setOpen(false);
  };

  const handleExcel = async () => {
    await downloadXLSX(data, filename, columns);
    setOpen(false);
  };

  return (
    <div ref={ref} className="relative inline-block">
      <button
        onClick={() => setOpen(!open)}
        className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md border border-input bg-background hover:bg-muted transition-colors"
      >
        <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
        </svg>
        {label}
        <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>
      {open && (
        <div className="absolute right-0 mt-1 w-36 rounded-md border border-input bg-background shadow-lg z-50">
          <button
            onClick={handleCSV}
            className="w-full px-3 py-2 text-left text-xs hover:bg-muted transition-colors rounded-t-md"
          >
            Export as CSV
          </button>
          <button
            onClick={handleExcel}
            className="w-full px-3 py-2 text-left text-xs hover:bg-muted transition-colors rounded-b-md"
          >
            Export as Excel
          </button>
        </div>
      )}
    </div>
  );
}
