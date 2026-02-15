import Link from "next/link";
import { listExperiments } from "@/lib/data-loader";
import { pct, fixed, usd, formatDate } from "@/lib/format";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

export const dynamic = "force-dynamic";

export default function ExperimentsPage() {
  const experiments = listExperiments();

  return (
    <div className="p-6 space-y-4">
      <div>
        <h1 className="text-2xl font-bold">Experiments</h1>
        <p className="text-sm text-muted-foreground mt-1">
          {experiments.length} experiment run{experiments.length !== 1 ? "s" : ""} found
        </p>
      </div>

      <div className="border rounded-md">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Model</TableHead>
              <TableHead>Baseline</TableHead>
              <TableHead>Date</TableHead>
              <TableHead className="text-right">F1</TableHead>
              <TableHead className="text-right">F2</TableHead>
              <TableHead className="text-right">Precision</TableHead>
              <TableHead className="text-right">Recall</TableHead>
              <TableHead className="text-right">Jaccard</TableHead>
              <TableHead className="text-right">Laziness</TableHead>
              <TableHead className="text-right">Cost</TableHead>
              <TableHead className="text-right">Samples</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {experiments.map((exp) => (
              <TableRow key={exp.run_id}>
                <TableCell>
                  <Link
                    href={`/experiments/${encodeURIComponent(exp.run_id)}`}
                    className="font-medium text-primary hover:underline"
                  >
                    {exp.model_key}
                  </Link>
                  <div className="text-xs text-muted-foreground">{exp.provider}</div>
                </TableCell>
                <TableCell>
                  <Badge variant="secondary">{exp.baseline_type}</Badge>
                </TableCell>
                <TableCell className="text-sm text-muted-foreground">
                  {formatDate(exp.timestamp)}
                </TableCell>
                <TableCell className="text-right font-mono">{fixed(exp.f1)}</TableCell>
                <TableCell className="text-right font-mono font-medium">{fixed(exp.f2)}</TableCell>
                <TableCell className="text-right font-mono">{fixed(exp.precision)}</TableCell>
                <TableCell className="text-right font-mono">{fixed(exp.recall)}</TableCell>
                <TableCell className="text-right font-mono">{fixed(exp.avg_jaccard)}</TableCell>
                <TableCell className="text-right font-mono">{pct(exp.laziness_rate)}</TableCell>
                <TableCell className="text-right font-mono">
                  {exp.total_cost_usd != null ? usd(exp.total_cost_usd) : "N/A"}
                </TableCell>
                <TableCell className="text-right">{exp.sample_count}</TableCell>
              </TableRow>
            ))}
            {experiments.length === 0 && (
              <TableRow>
                <TableCell colSpan={11} className="text-center text-muted-foreground py-12">
                  No experiments found. Run an experiment to see results here.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
