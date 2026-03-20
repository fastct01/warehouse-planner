import { ScenarioResult } from '@/lib/api'

interface Props {
  scenarios: ScenarioResult[]
  annualKwh: number
  annualCost: number
}

const fmt = (n: number | null | undefined, prefix = '', suffix = '') =>
  n == null ? '—' : `${prefix}${Math.round(n).toLocaleString()}${suffix}`

const fmtDecimal = (n: number | null | undefined, dp = 1) =>
  n == null ? '—' : n.toFixed(dp)

const CARD_STYLE: Record<string, string> = {
  solar_only: 'border-yellow-200 bg-yellow-50',
  solar_battery: 'border-blue-200 bg-blue-50',
  efficiency_bundle: 'border-green-200 bg-green-50',
}

export function ScenarioTable({ scenarios, annualKwh, annualCost }: Props) {
  const avgTariff = annualKwh > 0 ? annualCost / annualKwh : 0

  return (
    <div className="space-y-4">
      {/* Baseline */}
      <div className="border border-gray-200 bg-gray-50 rounded-xl p-5">
        <h3 className="font-semibold text-gray-700 mb-3 text-sm uppercase tracking-wide">Current baseline</h3>
        <div className="grid grid-cols-3 gap-4">
          <Stat label="Annual usage" value={`${Math.round(annualKwh).toLocaleString()} kWh`} />
          <Stat label="Annual cost" value={`£${Math.round(annualCost).toLocaleString()}`} />
          <Stat label="Avg tariff" value={`${(avgTariff * 100).toFixed(1)}p/kWh`} />
        </div>
      </div>

      {/* Scenario cards */}
      {scenarios.map(s => (
        <div key={s.id} className={`border rounded-xl p-5 ${CARD_STYLE[s.scenario_type] || 'border-gray-200 bg-white'}`}>
          <h3 className="font-semibold text-gray-900 mb-3">{s.name}</h3>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <Stat label="Capex" value={fmt(s.capex_gbp, '£')} />
            <Stat
              label="Annual savings"
              value={fmt(s.annual_savings_gbp, '£', '/yr')}
              sub={`${fmt(s.annual_savings_kwh)} kWh`}
              highlight="green"
            />
            <Stat label="Simple payback" value={`${fmtDecimal(s.payback_years)} yrs`} />
            <Stat
              label="NPV (20 yr)"
              value={fmt(s.npv_gbp, '£')}
              highlight={(s.npv_gbp ?? 0) >= 0 ? 'green' : 'red'}
            />
          </div>

          {s.assumptions && (
            <details className="mt-3 group">
              <summary className="text-xs text-gray-400 cursor-pointer hover:text-gray-600 select-none">
                View assumptions
              </summary>
              <div className="mt-2 grid grid-cols-2 sm:grid-cols-3 gap-x-4 gap-y-1 text-xs text-gray-500">
                {Object.entries(s.assumptions).map(([k, v]) => (
                  <div key={k}>
                    <span className="font-medium text-gray-600">{k.replace(/_/g, ' ')}:</span>{' '}
                    {String(v)}
                  </div>
                ))}
              </div>
            </details>
          )}
        </div>
      ))}

      <p className="text-xs text-gray-400 leading-relaxed">
        * Indicative estimates based on rule-of-thumb assumptions. Not a substitute for a detailed
        engineering assessment. Payback assumes flat energy prices. NPV uses 6% discount rate.
      </p>
    </div>
  )
}

function Stat({
  label,
  value,
  sub,
  highlight,
}: {
  label: string
  value: string
  sub?: string
  highlight?: 'green' | 'red'
}) {
  const valueClass =
    highlight === 'green'
      ? 'text-green-700'
      : highlight === 'red'
      ? 'text-red-600'
      : 'text-gray-900'

  return (
    <div>
      <p className="text-xs text-gray-500 mb-0.5">{label}</p>
      <p className={`text-lg font-bold ${valueClass}`}>{value}</p>
      {sub && <p className="text-xs text-gray-400">{sub}</p>}
    </div>
  )
}
