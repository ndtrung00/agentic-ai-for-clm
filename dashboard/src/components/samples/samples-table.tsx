"use client";

import { useState, useMemo } from "react";
import Link from "next/link";
import type { SampleSummary } from "@/lib/types";
import { fixed } from "@/lib/format";
import { ClassificationBadge, TierBadge } from "./classification-badge";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

interface SamplesTableProps {
  samples: SampleSummary[];
  runId: string;
}

export function SamplesTable({ samples, runId }: SamplesTableProps) {
  const [tierFilter, setTierFilter] = useState<string>("all");
  const [classFilter, setClassFilter] = useState<string>("all");
  const [search, setSearch] = useState("");
  const [sortKey, setSortKey] = useState<string>("category");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("asc");

  const filtered = useMemo(() => {
    let result = [...samples];
    if (tierFilter !== "all") result = result.filter((s) => s.tier === tierFilter);
    if (classFilter !== "all") result = result.filter((s) => s.classification === classFilter);
    if (search) {
      const q = search.toLowerCase();
      result = result.filter((s) => s.category.toLowerCase().includes(q) || s.id.toLowerCase().includes(q));
    }
    result.sort((a, b) => {
      const av = a[sortKey as keyof SampleSummary] ?? "";
      const bv = b[sortKey as keyof SampleSummary] ?? "";
      const cmp = typeof av === "number" && typeof bv === "number" ? av - bv : String(av).localeCompare(String(bv));
      return sortDir === "asc" ? cmp : -cmp;
    });
    return result;
  }, [samples, tierFilter, classFilter, search, sortKey, sortDir]);

  const toggleSort = (key: string) => {
    if (sortKey === key) setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    else { setSortKey(key); setSortDir("asc"); }
  };

  const SortHeader = ({ k, children }: { k: string; children: React.ReactNode }) => (
    <TableHead className="cursor-pointer select-none" onClick={() => toggleSort(k)}>
      {children} {sortKey === k ? (sortDir === "asc" ? "\u2191" : "\u2193") : ""}
    </TableHead>
  );

  return (
    <div className="space-y-3">
      <div className="flex gap-3 flex-wrap">
        <Input
          placeholder="Search category..."
          className="w-60"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <Select value={tierFilter} onValueChange={setTierFilter}>
          <SelectTrigger className="w-36"><SelectValue placeholder="Tier" /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All tiers</SelectItem>
            <SelectItem value="common">Common</SelectItem>
            <SelectItem value="moderate">Moderate</SelectItem>
            <SelectItem value="rare">Rare</SelectItem>
          </SelectContent>
        </Select>
        <Select value={classFilter} onValueChange={setClassFilter}>
          <SelectTrigger className="w-36"><SelectValue placeholder="Class" /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All classes</SelectItem>
            <SelectItem value="TP">TP</SelectItem>
            <SelectItem value="TN">TN</SelectItem>
            <SelectItem value="FP">FP</SelectItem>
            <SelectItem value="FN">FN</SelectItem>
          </SelectContent>
        </Select>
        <span className="text-sm text-muted-foreground self-center">
          {filtered.length} of {samples.length} samples
        </span>
      </div>

      <div className="border rounded-md">
        <Table>
          <TableHeader>
            <TableRow>
              <SortHeader k="category">Category</SortHeader>
              <SortHeader k="tier">Tier</SortHeader>
              <SortHeader k="classification">Class</SortHeader>
              <SortHeader k="jaccard">Jaccard</SortHeader>
              <SortHeader k="grounding_rate">Grounding</SortHeader>
              <TableHead />
            </TableRow>
          </TableHeader>
          <TableBody>
            {filtered.map((s) => (
              <TableRow key={s.id}>
                <TableCell className="font-medium">{s.category}</TableCell>
                <TableCell><TierBadge value={s.tier} /></TableCell>
                <TableCell><ClassificationBadge value={s.classification} /></TableCell>
                <TableCell>{fixed(s.jaccard)}</TableCell>
                <TableCell>{s.grounding_rate != null ? fixed(s.grounding_rate) : "N/A"}</TableCell>
                <TableCell>
                  <Link
                    href={`/experiments/${runId}/samples/${encodeURIComponent(s.id)}`}
                    className="text-sm text-primary hover:underline"
                  >
                    View
                  </Link>
                </TableCell>
              </TableRow>
            ))}
            {filtered.length === 0 && (
              <TableRow>
                <TableCell colSpan={6} className="text-center text-muted-foreground py-8">
                  No samples match the current filters.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
