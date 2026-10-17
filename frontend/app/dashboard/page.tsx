'use client'
import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { Navbar } from '@/components/Navbar'
import { api, Project } from '@/lib/api'

const BUILDING_LABELS: Record<string, string> = {
  office: 'Office',
  hospital: 'Hospital',
  data_centre: 'Data Centre',
  factory: 'Factory',
}

const PATTERN_LABELS: Record<string, string> = {
  '9-5_weekdays': '9–5 weekdays',
  extended_hours: 'Extended hours',
  '24_7': '24/7',
}

export default function DashboardPage() {
  const router = useRouter()
  const [projects, setProjects] = useState<Project[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.projects
      .list()
      .then(setProjects)
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  return (
    <div>
      <Navbar />
      <main className="max-w-5xl mx-auto px-6 py-10">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-2xl font-bold">Your projects</h1>
            <p className="text-gray-500 text-sm mt-1">Each project represents one building or site.</p>
          </div>
          <Link
            href="/projects/new"
            className="bg-green-600 text-white px-5 py-2 rounded-lg hover:bg-green-700 transition font-medium text-sm"
          >
            + New project
          </Link>
        </div>

        {loading && <p className="text-gray-400 text-sm">Loading…</p>}

        {!loading && projects.length === 0 && (
          <div className="text-center py-20 border-2 border-dashed border-gray-200 rounded-2xl">
            <p className="text-gray-400 mb-3">No projects yet.</p>
            <Link href="/projects/new" className="text-green-600 hover:underline font-medium text-sm">
              Create your first project →
            </Link>
          </div>
        )}

        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {projects.map(p => (
            <Link
              href={`/projects/${p.id}`}
              key={p.id}
              className="bg-white border border-gray-200 rounded-xl p-5 hover:border-green-300 hover:shadow-sm transition group"
            >
              <div className="flex items-start justify-between gap-2">
                <h2 className="font-semibold text-gray-900 group-hover:text-green-700 transition leading-tight">
                  {p.name}
                </h2>
                <span className="shrink-0 text-xs bg-green-50 text-green-700 px-2 py-0.5 rounded-full border border-green-100">
                  {PATTERN_LABELS[p.operating_pattern || ''] || p.operating_pattern}
                </span>
              </div>
              <p className="text-sm text-gray-500 mt-1">
                {BUILDING_LABELS[p.building_type] || p.building_type} · {p.location}
              </p>
              <p className="text-xs text-gray-300 mt-4">
                Created {new Date(p.created_at).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })}
              </p>
            </Link>
          ))}
        </div>
      </main>
    </div>
  )
}
