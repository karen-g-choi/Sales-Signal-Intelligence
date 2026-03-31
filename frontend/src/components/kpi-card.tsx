import { Card, CardContent, CardHeader } from "@/components/ui/card";

interface KpiCardProps {
  label: string;
  value: string;
  note: string;
  unitLabel?: string;
}

export function KpiCard({ label, value, note, unitLabel }: KpiCardProps) {
  return (
    <Card className="min-h-[220px] overflow-hidden">
      <CardHeader className="pb-2">
        <div className="min-h-[52px] text-[12px] font-medium uppercase tracking-[0.06em] leading-5 text-muted/90">
          {label}
        </div>
      </CardHeader>
      <CardContent className="flex flex-col pt-1">
        <div className="min-h-[66px] space-y-1">
          <div className="whitespace-nowrap text-[clamp(1.85rem,2.25vw,2.5rem)] font-bold leading-[1.02] tracking-[-0.045em] text-ink">
            {value}
          </div>
          {unitLabel ? (
            <div className="text-[11px] font-semibold uppercase tracking-[0.12em] text-slateblue/90">
              {unitLabel}
            </div>
          ) : null}
        </div>
        <p className="mt-2 max-w-[26ch] text-[13px] leading-5 text-muted">{note}</p>
      </CardContent>
    </Card>
  );
}
