'use client'
import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { Navbar } from '@/components/Navbar'
import { EnergyChart } from '@/components/EnergyChart'
import { ScenarioTable } from '@/components/ScenarioTable'
import BillUploader from '@/components/BillUploader'
import { api, ProjectDetail, ScenarioResult } from '@/lib/api'

export default function ProjectPage({ params }: { params: { id: string } }) {
  const router = useRouter()
  const projectId = parseInt(params.id)

  const [project, setProject] = useState<ProjectDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [running, setRunning] = useState(false)
  const [showUploader, setShowUploader] = useState(false)

  useEffect(() => {
    if (!localStorage.getItem('token')) {
      router.push('/login')
      return
    }
    api.projects
      .get(projectId)
      .then(setProject)
      .catch(() => router.push('/dashboard'))
      .finally(() => setLoading(false))
  }, [projectId, router])

  function refreshProject() {
    api.projects.get(projectId).then(setProject).catch(() => {})
  }

  async function rerunScenarios() {
    if (!project) return
    setRunning(true)
    try {
      const results: ScenarioResult[] = await api.scenarios.run(project.id)
      setProject(p => (p ? { ...p, scenario_results: results } : p))
    } finally {
      setRunning(false)
    }
  }

  if (loading) {
    return (
      <div>
        <Navbar />
        <main className="max-w-4xl mx-auto px-6 py-10">
          <p className="text-gray-400 text-sm">Loading…</p>
        </main>
      </div>
    )
  }
  if (!project) return null

  const annualKwh = project.monthly_bills.reduce((s, b) => s + b.kwh, 0)
  const annualCost = project.monthly_bills.reduce((s, b) => s + b.cost_gbp, 0)

  return (
    <div>
      <Navbar />
      <main className="max-w-4xl mx-auto px-6 py-10 space-y-6">

        {/* Header */}
        <div className="flex items-start justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 text-sm text-gray-400 mb-1">
              <Link href="/dashboard" className="hover:text-gray-600">Projects</Link>
              <span>/</span>
              <span className="text-gray-600">{project.name}</span>
            </div>
            <h1 className="text-2xl font-bold">{project.name}</h1>
            <p className="text-gray-500 text-sm mt-0.5">
              {project.building_type.replace('_', ' ')} · {project.location}
              {project.floor_area_m2 ? ` · ${project.floor_area_m2.toLocaleString()} m²` : ''}
            </p>
          </div>
          <button
            onClick={rerunScenarios}
            disabled={running}
            className="shrink-0 text-sm border border-gray-300 px-4 py-2 rounded-lg hover:bg-gray-50 transition disabled:opacity-60"
          >
            {running ? 'Running…' : '↺ Rerun scenarios'}
          </button>
        </div>

        {/* Bill upload */}
        <div className="bg-white border border-gray-200 rounded-2xl p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold">Upload bills</h2>
            <button
              onClick={() => setShowUploader((v) => !v)}
              className="text-sm text-green-600 hover:underline"
            >
              {showUploader ? 'Hide' : 'Show uploader'}
            </button>
          </div>
          {showUploader && (
            <BillUploader
              projectId={projectId}
              onBillApproved={refreshProject}
            />
          )}
          {!showUploader && (
            <p className="text-sm text-gray-400">
              Upload PDF or image bills — fields are extracted automatically for your review.
            </p>
          )}
        </div>

        {/* Energy charts */}
        {project.monthly_bills.length > 0 && (
          <div className="bg-white border border-gray-200 rounded-2xl p-6">
            <h2 className="font-semibold mb-5">Energy & cost overview</h2>
            <EnergyChart bills={project.monthly_bills} />

            <div className="mt-5 grid grid-cols-3 gap-4 pt-5 border-t border-gray-100">
              <div>
                <p className="text-xs text-gray-400">Annual usage</p>
                <p className="text-lg font-bold">{Math.round(annualKwh).toLocaleString()} kWh</p>
              </div>
              <div>
                <p className="text-xs text-gray-400">Annual cost</p>
                <p className="text-lg font-bold">£{Math.round(annualCost).toLocaleString()}</p>
              </div>
              <div>
                <p className="text-xs text-gray-400">Avg tariff</p>
                <p className="text-lg font-bold">
                  {annualKwh > 0 ? ((annualCost / annualKwh) * 100).toFixed(1) : '—'}p/kWh
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Scenarios */}
        <div className="bg-white border border-gray-200 rounded-2xl p-6">
          <div className="flex items-center justify-between mb-5">
            <h2 className="font-semibold">Upgrade scenarios</h2>
            {project.scenario_results.length === 0 && (
              <button
                onClick={rerunScenarios}
                disabled={running}
                className="bg-green-600 text-white text-sm px-4 py-1.5 rounded-lg hover:bg-green-700 transition disabled:opacity-60"
              >
                {running ? 'Running…' : 'Run scenarios'}
              </button>
            )}
          </div>

          {project.scenario_results.length > 0 ? (
            <ScenarioTable
              scenarios={project.scenario_results}
              annualKwh={annualKwh}
              annualCost={annualCost}
            />
          ) : (
            <p className="text-gray-400 text-sm">
              No scenarios run yet.{' '}
              {project.monthly_bills.length === 0
                ? 'Add bill data first.'
                : 'Click "Run scenarios" to generate analysis.'}
            </p>
          )}
        </div>
      </main>
    </div>
  )
}
