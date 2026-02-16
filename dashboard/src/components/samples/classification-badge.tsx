import { Badge } from "@/components/ui/badge";
import { classificationColors, tierColors } from "@/lib/colors";

export function ClassificationBadge({ value }: { value: string }) {
  const c = classificationColors[value] ?? { bg: "bg-gray-50", text: "text-gray-700", border: "border-gray-200" };
  return (
    <Badge variant="outline" className={`${c.bg} ${c.text} ${c.border}`}>
      {value}
    </Badge>
  );
}

export function TierBadge({ value }: { value: string }) {
  const c = tierColors[value] ?? { bg: "bg-gray-50", text: "text-gray-700", border: "border-gray-200" };
  return (
    <Badge variant="outline" className={`${c.bg} ${c.text} ${c.border}`}>
      {value}
    </Badge>
  );
}
