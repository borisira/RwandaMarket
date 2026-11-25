/// <reference types="vite/client" />

export const API_BASE = (import.meta.env.VITE_API_BASE_URL || '/api').replace(/\/$/, '')

const TOKEN_STORAGE_KEY = 'landlink_token'
const LEGACY_TOKEN_STORAGE_KEY = 'rwm_token'

export function getToken(): string | null {
  const token = localStorage.getItem(TOKEN_STORAGE_KEY) || localStorage.getItem(LEGACY_TOKEN_STORAGE_KEY)
  if (token) {
    localStorage.setItem(TOKEN_STORAGE_KEY, token)
    localStorage.removeItem(LEGACY_TOKEN_STORAGE_KEY)
  }
  return token
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_STORAGE_KEY)
  localStorage.removeItem(LEGACY_TOKEN_STORAGE_KEY)
}

export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers)
  headers.set('Accept', 'application/json')
  if (options.body && !(options.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json')
  }
  const token = getToken()
  if (token) headers.set('Authorization', `Token ${token}`)

  const response = await fetch(`${API_BASE}${path}`, { ...options, headers })
  if (response.status === 204) return undefined as T
  const contentType = response.headers.get('content-type') ?? ''
  const payload = contentType.includes('application/json')
    ? await response.json() as unknown
    : await response.text()

  if (!response.ok) {
    const data = payload as { detail?: string; [key: string]: unknown }
    const message = data && typeof data === 'object'
      ? data.detail ?? Object.entries(data).map(([key, value]) => `${key}: ${Array.isArray(value) ? value.join(', ') : String(value)}`).join(' · ')
      : String(payload)
    throw new Error(message || `Request failed (${response.status})`)
  }
  return payload as T
}

export function jsonBody(value: unknown): string {
  return JSON.stringify(value)
}
