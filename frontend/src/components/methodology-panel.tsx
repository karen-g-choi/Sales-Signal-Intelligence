import { Card, CardContent, CardHeader } from "@/components/ui/card";

export function MethodologyPanel({ items }: { items: string[] }) {
  return (
    <Card>
      <CardHeader>
        <h3 className="text-lg font-semibold text-ink">Business Logic in Plain English</h3>
      </CardHeader>
      <CardContent>
        <ul className="space-y-3 text-sm leading-6 text-muted">
          {items.map((item) => (
            <li key={item} className="border-b border-slate-100 pb-3 last:border-0 last:pb-0">
              {item}
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  );
}
