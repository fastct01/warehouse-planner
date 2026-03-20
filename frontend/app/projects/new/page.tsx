'use client'
import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { Navbar } from '@/components/Navbar'
import { api, MonthlyBillCreate } from '@/lib/api'

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

const BUILDING_TYPES = [
  { value: 'office', label: 'Office' },
  { value: 'hospital', label: 'Hospital' },
  { value: 'data_centre', label: 'Data Centre' },
  { value: 'factory', label: 'Factory' },
]

const OPERATING_PATTERNS = [
  { value: '9-5_weekdays', label: '9–5 weekdays' },
  { value: 'extended_hours', label: 'Extended hours (7am–10pm)' },
  { value: '24_7', label: '24/7' },
]

type Step = 1 | 2

interface BillRow {
  year: number
  month: number
  kwh: string
  cost_gbp: string
}

export default function NewProjectPage() {
  const router = useRouter()
  const [step, setStep] = useState<Step>(1)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [projectId, setProjectId] = useState<number | null>(null)

  // Step 1 – building details
  const [details, setDetails] = useState({
    name: '',
    building_type: 'office',
    location: '',
    floor_area_m2: '',
    operating_pattern: '9-5_weekdays',
  })

  // Step 2 – 12 months of bills (default to previous calendar year)
  const prevYear = new Date().getFullYear() - 1
  const [bills, setBills] = useState<BillRow[]>(
    Array.from({ length: 12 }, (_, i) => ({ year: prevYear, month: i + 1, kwh: '', cost_gbp: '' }))
  )

  const setDetail =
    (k: keyof typeof details) =>
    (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) =>
      setDetails(d => ({ ...d, [k]: e.target.value }))

  const setBill = (i: number, k: 'kwh' | 'cost_gbp', v: string) =>
    setBills(b => b.map((row, idx) => (idx === i ? { ...row, [k]: v } : row)))

  async function handleCreateProject() {
    setSaving(true)
    setError('')
    try {
      const project = await api.projects.create({
        name: details.name,
        building_type: details.building_type,
        location: details.location,
        floor_area_m2: details.floor_area_m2 ? parseFloat(details.floor_area_m2) : undefined,
        operating_pattern: details.operating_pattern,
      })
      setProjectId(project.id)
      setStep(2)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to create project')
    } finally {
      setSaving(false)
    }
  }

  async function handleSaveBills() {
    if (!projectId) return
    const validBills: MonthlyBillCreate[] = bills
      .filter(b => b.kwh && b.cost_gbp)
      .map(b => ({ year: b.year, month: b.month, kwh: parseFloat(b.kwh), cost_gbp: parseFloat(b.cost_gbp) }))

    if (validBills.length < 6) {
      setError('Please enter at least 6 months of data.')
      return
    }

    setSaving(true)
    setError('')
    try {
      await api.bills.saveManual(projectId, validBills)
      await api.scenarios.run(projectId)
      router.push(`/projects/${projectId}`)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to save bills')
    } finally {
      setSaving(false)
    }
  }

  const totalKwh = bills.reduce((s, b) => s + (parseFloat(b.kwh) || 0), 0)
  const totalCost = bills.reduce((s, b) => s + (parseFloat(b.cost_gbp) || 0), 0)

  return (
    <div>
      <Navbar />
      <main className="max-w-2xl mx-auto px-6 py-10">
        {/* Step indicator */}
        <div className="flex items-center gap-3 mb-8">
          {([1, 2] as Step[]).map((s, idx) => (
            <div key={s} className="flex items-center gap-3">
              <div
                className={`w-7 h-7 rounded-full flex items-center justify-center text-sm font-semibold ${
                  step >= s ? 'bg-green-600 text-white' : 'bg-gray-200 text-gray-400'
                }`}
              >
                {s}
              </div>
              {idx < 1 && <div className={`h-0.5 w-12 ${step > s ? 'bg-green-600' : 'bg-gray-200'}`} />}
            </div>
          ))}
          <span className="ml-1 text-sm text-gray-500">
            {step === 1 ? 'Building details' : 'Monthly bill data'}
          </span>
        </div>

        {/* ── Step 1: Building details ────────────────────────────────────────── */}
        {step === 1 && (
          <div className="bg-white rounded-2xl border border-gray-200 p-8">
            <h1 className="text-xl font-bold mb-1">Tell us about the building</h1>
            <p className="text-sm text-gray-500 mb-6">This shapes the scenario calculations.</p>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Project name</label>
                <input
                  type="text"
                  value={details.name}
                  onChange={setDetail('name')}
                  required
                  placeholder="e.g. Head Office – Manchester"
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-green-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Building type</label>
                  <select
                    value={details.building_type}
                    onChange={setDetail('building_type')}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-green-500"
                  >
                    {BUILDING_TYPES.map(t => (
                      <option key={t.value} value={t.value}>{t.label}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Operating pattern</label>
                  <select
                    value={details.operating_pattern}
                    onChange={setDetail('operating_pattern')}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-green-500"
                  >
                    {OPERATING_PATTERNS.map(o => (
                      <option key={o.value} value={o.value}>{o.label}</option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Location (city)</label>
                  <input
                    type="text"
                    value={details.location}
                    onChange={setDetail('location')}
                    required
                    placeholder="e.g. Manchester"
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-green-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Floor area (m²) <span className="text-gray-400 font-normal">optional</span>
                  </label>
                  <input
                    type="number"
                    value={details.floor_area_m2}
                    onChange={setDetail('floor_area_m2')}
                    min="0"
                    placeholder="e.g. 2500"
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-green-500"
                  />
                </div>
              </div>
            </div>

            {error && <p className="text-red-600 text-sm mt-4">{error}</p>}

            <button
              onClick={handleCreateProject}
              disabled={saving || !details.name || !details.location}
              className="mt-6 w-full bg-green-600 hover:bg-green-700 text-white font-medium py-2 rounded-lg transition disabled:opacity-60 text-sm"
            >
              {saving ? 'Saving…' : 'Next: Add bill data →'}
            </button>
          </div>
        )}

        {/* ── Step 2: Monthly bills ───────────────────────────────────────────── */}
        {step === 2 && (
          <div className="bg-white rounded-2xl border border-gray-200 p-8">
            <h1 className="text-xl font-bold mb-1">Monthly electricity bills</h1>
            <p className="text-sm text-gray-500 mb-6">
              Read from your actual bills. At least 6 months required. Leave blank to skip a month.
            </p>

            <div className="overflow-x-auto -mx-2">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-gray-400 border-b border-gray-100">
                    <th className="pb-2 pl-2 font-medium w-24">Month</th>
                    <th className="pb-2 font-medium">Usage (kWh)</th>
                    <th className="pb-2 font-medium">Cost (£)</th>
                  </tr>
                </thead>
                <tbody>
                  {bills.map((b, i) => (
                    <tr key={i} className="border-b border-gray-50">
                      <td className="py-1.5 pl-2 text-gray-600 font-medium">
                        {MONTHS[b.month - 1]} {b.year}
                      </td>
                      <td className="py-1.5 pr-2">
                        <input
                          type="number"
                          min="0"
                          step="1"
                          value={b.kwh}
                          onChange={e => setBill(i, 'kwh', e.target.value)}
                          placeholder="0"
                          className="w-full border border-gray-200 rounded px-2 py-1 text-sm focus:outline-none focus:ring-1 focus:ring-green-500"
                        />
                      </td>
                      <td className="py-1.5">
                        <input
                          type="number"
                          min="0"
                          step="0.01"
                          value={b.cost_gbp}
                          onChange={e => setBill(i, 'cost_gbp', e.target.value)}
                          placeholder="0.00"
                          className="w-full border border-gray-200 rounded px-2 py-1 text-sm focus:outline-none focus:ring-1 focus:ring-green-500"
                        />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {totalKwh > 0 && (
              <div className="mt-4 bg-gray-50 rounded-lg px-4 py-3 text-sm text-gray-600 flex gap-6">
                <span>
                  Total: <strong>{Math.round(totalKwh).toLocaleString()} kWh</strong>
                </span>
                <span>
                  Cost: <strong>£{totalCost.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</strong>
                </span>
                <span>
                  Avg tariff:{' '}
                  <strong>{totalKwh > 0 ? ((totalCost / totalKwh) * 100).toFixed(1) : '—'}p/kWh</strong>
                </span>
              </div>
            )}

            {error && <p className="text-red-600 text-sm mt-4">{error}</p>}

            <button
              onClick={handleSaveBills}
              disabled={saving}
              className="mt-6 w-full bg-green-600 hover:bg-green-700 text-white font-medium py-2 rounded-lg transition disabled:opacity-60 text-sm"
            >
              {saving ? 'Running analysis…' : 'Save & run scenarios →'}
            </button>
          </div>
        )}
      </main>
    </div>
  )
}
