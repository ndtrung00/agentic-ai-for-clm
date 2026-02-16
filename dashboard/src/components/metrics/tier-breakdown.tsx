"use client";

import type { TierMetrics } from "@/lib/types";
import { fixed, pct } from "@/lib/format";
import { tierColors } from "@/lib/colors";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";

interface TierBreakdownProps {
  perTier: Record<string, TierMetrics>;
}

const TIER_ORDER = ["common", "moderate", "rare"];

export function TierBreakdown({ perTier }: TierBreakdownProps) {
  const tiers = TIER_ORDER.filter((t) => t in perTier);

  const chartData = tiers.map((tier) => ({
    tier: tier.charAt(0).toUpperCase() + tier.slice(1),
    F1: Number((perTier[tier].f1 * 100).toFixed(1)),
    F2: Number((perTier[tier].f2 * 100).toFixed(1)),
    Jaccard: Number((perTier[tier].avg_jaccard * 100).toFixed(1)),
  }));

  return (
    <div className="space-y-4">
      <h3 className="text-sm font-medium">Per-Tier Breakdown</h3>

      {/* Chart */}
      <div className="h-52">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData} barGap={2}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="tier" fontSize={12} />
            <YAxis domain={[0, 100]} fontSize={12} tickFormatter={(v) => `${v}%`} />
            <Tooltip formatter={(v) => `${v}%`} />
            <Legend />
            <Bar dataKey="F1" fill="#3b82f6" radius={[2, 2, 0, 0]} />
            <Bar dataKey="F2" fill="#8b5cf6" radius={[2, 2, 0, 0]} />
            <Bar dataKey="Jaccard" fill="#06b6d4" radius={[2, 2, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Table */}
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Tier</TableHead>
            <TableHead className="text-right">TP</TableHead>
            <TableHead className="text-right">FP</TableHead>
            <TableHead className="text-right">FN</TableHead>
            <TableHead className="text-right">TN</TableHead>
            <TableHead className="text-right">F1</TableHead>
            <TableHead className="text-right">F2</TableHead>
            <TableHead className="text-right">Jaccard</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {tiers.map((tier) => {
            const m = perTier[tier];
            const c = tierColors[tier];
            return (
              <TableRow key={tier}>
                <TableCell>
                  <Badge variant="outline" className={`${c.bg} ${c.text} ${c.border}`}>
                    {tier}
                  </Badge>
                </TableCell>
                <TableCell className="text-right">{m.tp}</TableCell>
                <TableCell className="text-right">{m.fp}</TableCell>
                <TableCell className="text-right">{m.fn}</TableCell>
                <TableCell className="text-right">{m.tn}</TableCell>
                <TableCell className="text-right font-medium">{fixed(m.f1)}</TableCell>
                <TableCell className="text-right font-medium">{fixed(m.f2)}</TableCell>
                <TableCell className="text-right">{fixed(m.avg_jaccard)}</TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
    </div>
  );
}
