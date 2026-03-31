import type { ReactNode } from "react";

import { Card, CardContent, CardHeader } from "@/components/ui/card";

interface TableCardProps {
  title: string;
  subtitle?: string;
  children: ReactNode;
}

export function TableCard({ title, subtitle, children }: TableCardProps) {
  return (
    <Card>
      <CardHeader className="pb-4">
        <h3 className="text-balance text-xl font-semibold tracking-[-0.02em] text-ink">{title}</h3>
        {subtitle ? <p className="text-pretty mt-1.5 max-w-3xl text-sm leading-6 text-muted">{subtitle}</p> : null}
      </CardHeader>
      <CardContent>{children}</CardContent>
    </Card>
  );
}
