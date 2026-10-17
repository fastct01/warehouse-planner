'use client'
import Link from 'next/link'

export function Navbar() {
  return (
    <nav className="bg-white border-b border-gray-200 px-6 py-3 flex items-center justify-between">
      <Link href="/dashboard" className="text-lg font-bold text-green-700 tracking-tight">
        Energy Advisor
      </Link>
      <div className="flex items-center gap-4">
        <Link href="/dashboard" className="text-sm text-gray-600 hover:text-gray-900">
          Projects
        </Link>
        <Link
          href="/projects/new"
          className="bg-green-600 text-white text-sm px-4 py-1.5 rounded-lg hover:bg-green-700 transition"
        >
          + New project
        </Link>
      </div>
    </nav>
  )
}
