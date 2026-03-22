const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

function getToken(): string | null {
  if (typeof window === 'undefined') return null
  return localStorage.getItem('token')
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken()
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(options.headers as Record<string, string> || {}),
    },
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || 'Request failed')
  }
  return res.json()
}

export const api = {
  auth: {
    register: (email: string, password: string, full_name?: string) =>
      request<{ access_token: string }>('/auth/register', {
        method: 'POST',
        body: JSON.stringify({ email, password, full_name }),
      }),
    login: (email: string, password: string) =>
      request<{ access_token: string }>('/auth/login', {
        method: 'POST',
        body: JSON.stringify({ email, password }),
      }),
    me: () => request<UserOut>('/auth/me'),
  },
  projects: {
    list: () => request<Project[]>('/projects'),
    create: (data: ProjectCreate) =>
      request<Project>('/projects', { method: 'POST', body: JSON.stringify(data) }),
    get: (id: number) => request<ProjectDetail>(`/projects/${id}`),
    delete: (id: number) => request(`/projects/${id}`, { method: 'DELETE' }),
  },
  bills: {
    saveManual: (projectId: number, bills: MonthlyBillCreate[]) =>
      request<MonthlyBill[]>(`/projects/${projectId}/bills/manual`, {
        method: 'POST',
        body: JSON.stringify(bills),
      }),
    uploadFile: (projectId: number, file: File): Promise<Upload> => {
      const token = getToken()
      const form = new FormData()
      form.append('file', file)
      return fetch(`${API_BASE}/projects/${projectId}/bills/upload`, {
        method: 'POST',
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        body: form,
      }).then(async (res) => {
        if (!res.ok) {
          const err = await res.json().catch(() => ({ detail: res.statusText }))
          throw new Error(err.detail || 'Upload failed')
        }
        return res.json()
      })
    },
    listUploads: (projectId: number) =>
      request<Upload[]>(`/projects/${projectId}/bills/uploads`),
    getUpload: (projectId: number, uploadId: number) =>
      request<Upload>(`/projects/${projectId}/bills/uploads/${uploadId}`),
    getUploadResult: (projectId: number, uploadId: number) =>
      request<BillRaw>(`/projects/${projectId}/bills/uploads/${uploadId}/result`),
    patchUploadResult: (projectId: number, uploadId: number, data: Partial<BillRaw>) =>
      request<BillRaw>(`/projects/${projectId}/bills/uploads/${uploadId}/result`, {
        method: 'PATCH',
        body: JSON.stringify(data),
      }),
  },
  scenarios: {
    run: (projectId: number, params?: { solar_kw?: number; battery_kwh?: number }) =>
      request<ScenarioResult[]>(`/projects/${projectId}/scenarios/run`, {
        method: 'POST',
        body: JSON.stringify(params || {}),
      }),
  },
}

// ── Types ──────────────────────────────────────────────────────────────────────

export interface UserOut {
  id: number
  email: string
  full_name?: string
  created_at: string
}

export interface Project {
  id: number
  name: string
  building_type: string
  location: string
  floor_area_m2: number | null
  operating_pattern: string | null
  user_id: number
  created_at: string
}

export interface ProjectDetail extends Project {
  monthly_bills: MonthlyBill[]
  scenario_results: ScenarioResult[]
}

export interface ProjectCreate {
  name: string
  building_type: string
  location: string
  floor_area_m2?: number
  operating_pattern?: string
}

export interface MonthlyBill {
  id: number
  project_id: number
  year: number
  month: number
  kwh: number
  cost_gbp: number
  peak_demand_kw: number | null
  tariff_name: string | null
}

export interface MonthlyBillCreate {
  year: number
  month: number
  kwh: number
  cost_gbp: number
  peak_demand_kw?: number
  tariff_name?: string
}

export interface Upload {
  id: number
  project_id: number
  filename: string
  file_type: string
  status: 'pending' | 'processing' | 'done' | 'failed'
  error_message?: string
  created_at: string
}

export interface BillRaw {
  id: number
  upload_id: number
  project_id: number
  bill_period_start: string | null
  bill_period_end: string | null
  kwh: number | null
  total_cost: number | null
  peak_kw: number | null
  tariff_name: string | null
  supplier: string | null
  currency: string
  confidence: number
  extraction_method: string
  status: string
  created_at: string
}

export interface ScenarioResult {
  id: number
  project_id: number
  scenario_type: string
  name: string
  capex_gbp: number
  annual_savings_kwh: number
  annual_savings_gbp: number
  payback_years: number | null
  npv_gbp: number | null
  assumptions: Record<string, unknown> | null
  created_at: string
}
