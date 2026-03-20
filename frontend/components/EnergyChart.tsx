'use client'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'
import { MonthlyBill } from '@/lib/api'

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

interface Props {
  bills: MonthlyBill[]
}

export function EnergyChart({ bills }: Props) {
  const sorted = [...bills].sort((a, b) =>
    a.year !== b.year ? a.year - b.year : a.month - b.month
  )

  const kwhData = sorted.map(b => ({
    label: `${MONTHS[b.month - 1]} ${String(b.year).slice(2)}`,
    kWh: Math.round(b.kwh),
  }))

  const costData = sorted.map(b => ({
    label: `${MONTHS[b.month - 1]} ${String(b.year).slice(2)}`,
    '£': Math.round(b.cost_gbp),
  }))

  return (
    <div className="grid sm:grid-cols-2 gap-8">
      <div>
        <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-3">Monthly usage (kWh)</p>
        <ResponsiveContainer width="100%" height={180}>
          <BarChart data={kwhData} margin={{ top: 0, right: 0, left: -20, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f3f4f6" />
            <XAxis dataKey="label" tick={{ fontSize: 10 }} tickLine={false} axisLine={false} />
            <YAxis tick={{ fontSize: 10 }} tickLine={false} axisLine={false} />
            <Tooltip
              formatter={(v: number) => [v.toLocaleString() + ' kWh', 'Usage']}
              contentStyle={{ fontSize: 12, borderRadius: 8 }}
            />
            <Bar dataKey="kWh" fill="#16a34a" radius={[3, 3, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div>
        <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-3">Monthly spend (£)</p>
        <ResponsiveContainer width="100%" height={180}>
          <BarChart data={costData} margin={{ top: 0, right: 0, left: -20, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f3f4f6" />
            <XAxis dataKey="label" tick={{ fontSize: 10 }} tickLine={false} axisLine={false} />
            <YAxis tick={{ fontSize: 10 }} tickLine={false} axisLine={false} />
            <Tooltip
              formatter={(v: number) => ['£' + v.toLocaleString(), 'Spend']}
              contentStyle={{ fontSize: 12, borderRadius: 8 }}
            />
            <Bar dataKey="£" fill="#0ea5e9" radius={[3, 3, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
