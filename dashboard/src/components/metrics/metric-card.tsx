import { Card, CardContent } from "@/components/ui/card";

interface MetricCardProps {
  label: string;
  value: string;
  sublabel?: string;
  highlight?: boolean;
}

export function MetricCard({ label, value, sublabel, highlight }: MetricCardProps) {
  return (
    <Card className={highlight ? "border-primary" : ""}>
      <CardContent className="pt-4 pb-3 px-4">
        <p className="text-xs text-muted-foreground uppercase tracking-wide">{label}</p>
        <p className="text-2xl font-bold mt-1">{value}</p>
        {sublabel && <p className="text-xs text-muted-foreground mt-1">{sublabel}</p>}
      </CardContent>
    </Card>
  );
}
