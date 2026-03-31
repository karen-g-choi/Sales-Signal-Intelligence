interface PageHeaderProps {
  title: string;
  subtitle: string;
}

export function PageHeader({ title, subtitle }: PageHeaderProps) {
  return (
    <div className="space-y-3">
      <p className="text-sm font-semibold uppercase tracking-[0.14em] text-slateblue">Commercial Analytics</p>
      <h1 className="text-balance text-[clamp(2.25rem,4vw,3.15rem)] font-bold leading-[1.02] tracking-[-0.04em] text-ink">
        {title}
      </h1>
      <p className="text-pretty max-w-3xl text-[15px] leading-7 text-muted">{subtitle}</p>
    </div>
  );
}
