import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { PageHeader } from "@/components/page-header";
import { Slider } from "@/components/ui/slider";
import { Switch } from "@/components/ui/switch";
import type { DashboardData, RuleConfig } from "@/lib/types";
import { formatCurrency, formatPercent } from "@/lib/utils";

interface RuleConfigurationPageProps {
  config: RuleConfig;
  onChange: (next: RuleConfig) => void;
  data: DashboardData;
}

export function RuleConfigurationPage({ config, onChange, data }: RuleConfigurationPageProps) {
  const activeSignals = data.riskRows.filter((row) => row.severity !== "Normal");

  return (
    <>
      <PageHeader
        title="Rule Configuration"
        subtitle="A business-friendly settings panel for adjusting signal sensitivity by context without exposing backend complexity."
      />

      <section className="grid gap-6 xl:grid-cols-[0.9fr_1.1fr]">
        <Card>
          <CardHeader>
            <h2 className="text-xl font-semibold text-ink">Detection Settings</h2>
            <p className="mt-2 text-sm leading-6 text-muted">
              These controls are designed to feel like a BI or ERP settings screen rather than a developer console.
            </p>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="rounded-2xl border border-slate-100 bg-slate-50 p-4">
              <div className="flex items-center justify-between">
                <div>
                  <div className="font-medium text-ink">Monthly basis</div>
                  <div className="text-sm text-muted">Use monthly interpretation for visible risk classification.</div>
                </div>
                <Switch
                  checked={config.detectionBasis === "monthly"}
                  onCheckedChange={(checked) =>
                    onChange({
                      ...config,
                      detectionBasis: checked ? "monthly" : "weekly",
                    })
                  }
                />
              </div>
            </div>

            <SettingRow
              label="Drop threshold"
              value={formatPercent(config.warningDropPct)}
              control={<Slider value={config.warningDropPct * 100} min={3} max={20} onChange={(value) => onChange({ ...config, warningDropPct: value / 100 })} />}
            />
            <SettingRow
              label="Critical threshold"
              value={formatPercent(config.criticalDropPct)}
              control={<Slider value={config.criticalDropPct * 100} min={5} max={30} onChange={(value) => onChange({ ...config, criticalDropPct: value / 100 })} />}
            />
            <SettingRow
              label="Minimum duration"
              value={`${config.minimumDuration} periods`}
              control={<Slider value={config.minimumDuration} min={2} max={6} onChange={(value) => onChange({ ...config, minimumDuration: value })} />}
            />
            <SettingRow
              label="Consistency threshold"
              value={formatPercent(config.consistencyThreshold)}
              control={<Slider value={config.consistencyThreshold * 100} min={40} max={90} step={5} onChange={(value) => onChange({ ...config, consistencyThreshold: value / 100 })} />}
            />
            <SettingRow
              label="High-impact threshold"
              value={formatCurrency(config.highImpactThreshold)}
              control={<Slider value={config.highImpactThreshold} min={5000} max={60000} step={5000} onChange={(value) => onChange({ ...config, highImpactThreshold: value })} />}
            />

            <div className="grid gap-4 md:grid-cols-2">
              <NumericInput
                label="Large-customer weighting"
                value={config.largeCustomerWeight}
                onChange={(value) => onChange({ ...config, largeCustomerWeight: Number(value) || 1 })}
              />
              <NumericInput
                label="Key-category weighting"
                value={config.keyCategoryWeight}
                onChange={(value) => onChange({ ...config, keyCategoryWeight: Number(value) || 1 })}
              />
            </div>
          </CardContent>
        </Card>

        <div className="space-y-6">
          <Card>
            <CardHeader>
              <h2 className="text-xl font-semibold text-ink">Current Signal Preview</h2>
              <p className="mt-2 text-sm text-muted">The frontend recalculates visible classifications as you adjust the business rules.</p>
            </CardHeader>
            <CardContent>
              <div className="grid gap-4 md:grid-cols-3">
                <PreviewMetric label="Active signals" value={`${activeSignals.length}`} />
                <PreviewMetric label="Critical" value={`${activeSignals.filter((row) => row.severity === "Critical").length}`} />
                <PreviewMetric label="Warnings" value={`${activeSignals.filter((row) => row.severity === "Warning").length}`} />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <h2 className="text-xl font-semibold text-ink">Updated Classification Sample</h2>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto">
                <table className="min-w-full text-left text-sm">
                  <thead className="border-b border-slate-100 text-muted">
                    <tr>
                      <th className="pb-4 font-medium">Customer</th>
                      <th className="pb-4 font-medium">Category</th>
                      <th className="pb-4 font-medium">Severity</th>
                      <th className="pb-4 font-medium">Delta %</th>
                      <th className="pb-4 font-medium">Risk Factor</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.riskRows.slice(0, 8).map((row) => (
                      <tr key={`${row.customer}-${row.category}`} className="border-b border-slate-50">
                        <td className="py-4 font-medium text-ink">{row.customer}</td>
                        <td className="py-4 text-muted">{row.category}</td>
                        <td className="py-4">{row.severity}</td>
                        <td className="py-4">{formatPercent(row.deltaPct)}</td>
                        <td className="py-4">{row.possibleRiskFactor}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </div>
      </section>
    </>
  );
}

function SettingRow({ label, value, control }: { label: string; value: string; control: ReactNode }) {
  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium text-ink">{label}</span>
        <span className="text-sm text-muted">{value}</span>
      </div>
      {control}
    </div>
  );
}

function NumericInput({ label, value, onChange }: { label: string; value: number; onChange: (value: string) => void }) {
  return (
    <div className="space-y-2">
      <label className="text-sm font-medium text-ink">{label}</label>
      <Input value={String(value)} onChange={(event) => onChange(event.target.value)} />
    </div>
  );
}

function PreviewMetric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-2xl bg-slate-50 p-4">
      <div className="text-sm text-muted">{label}</div>
      <div className="mt-2 text-2xl font-semibold text-ink">{value}</div>
    </div>
  );
}
import type { ReactNode } from "react";
