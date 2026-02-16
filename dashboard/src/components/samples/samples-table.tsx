"use client";

import { useState, useMemo } from "react";
import { useRouter } from "next/navigation";
import type { SampleSummary } from "@/lib/types";
import { fixed } from "@/lib/format";
import { ClassificationBadge, TierBadge } from "./classification-badge";
import { Badge } from "@/components/ui/badge";
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

const AGENT_SHORT: Record<string, string> = {
  risk_liability: "Risk",
  temporal_renewal: "Temporal",
  ip_commercial: "IP",
};

interface SamplesTableProps {
  samples: SampleSummary[];
  runId: string;
  routingTable?: Record<string, string>;
}

export function SamplesTable({ samples, runId, routingTable }: SamplesTableProps) {
  const router = useRouter();
  const [tierFilter, setTierFilter] = useState<string>("all");
  const [classFilter, setClassFilter] = useState<string>("all");
  const [search, setSearch] = useState("");
  const [sortKey, setSortKey] = useState<string>("category");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("asc");

  const hasRouting = !!routingTable;

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

  const colSpan = hasRouting ? 7 : 6;

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
              {hasRouting && <TableHead>Agent</TableHead>}
            </TableRow>
          </TableHeader>
          <TableBody>
            {filtered.map((s) => {
              const agent = routingTable?.[s.category];
              return (
                <TableRow
                  key={s.id}
                  className="cursor-pointer hover:bg-muted/50"
                  onClick={() => router.push(`/experiments/${runId}/samples/${encodeURIComponent(s.id)}`)}
                >
                  <TableCell className="font-medium">{s.category}</TableCell>
                  <TableCell><TierBadge value={s.tier} /></TableCell>
                  <TableCell><ClassificationBadge value={s.classification} /></TableCell>
                  <TableCell>{fixed(s.jaccard)}</TableCell>
                  <TableCell>{s.grounding_rate != null ? fixed(s.grounding_rate) : "N/A"}</TableCell>
                  {hasRouting && (
                    <TableCell>
                      {agent ? (
                        <Badge variant="outline" className="text-xs">
                          {AGENT_SHORT[agent] ?? agent}
                        </Badge>
                      ) : (
                        <span className="text-muted-foreground text-xs">N/A</span>
                      )}
                    </TableCell>
                  )}
                </TableRow>
              );
            })}
            {filtered.length === 0 && (
              <TableRow>
                <TableCell colSpan={colSpan} className="text-center text-muted-foreground py-8">
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
