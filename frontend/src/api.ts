export class ApiError extends Error {
  constructor(message: string, public status: number) {
    super(message)
  }
}

export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  let response: Response
  try {
    response = await fetch(path, {
      ...options,
      headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
    })
  } catch {
    throw new Error('Não foi possível conectar à API Flask.')
  }

  const body = response.status === 204 ? null : await response.json().catch(() => null)
  if (!response.ok) {
    if (response.status === 401 && path !== '/api/auth/login') {
      window.dispatchEvent(new CustomEvent('machry:session-expired'))
    }
    throw new ApiError(body?.erro || `Erro HTTP ${response.status}`, response.status)
  }
  return body as T
}

/** Envelope das rotas com paginação do backend. */
export interface PaginatedResponse<T> {
  items: T[]
  page: number
  per_page: number
  total: number
  pages: number
}

/**
 * Percorre as páginas da API para abastecer seletores e telas que dependem do
 * catálogo completo. Mantém compatibilidade com respostas antigas em array.
 * A API limita per_page a 100; não assume que os 20 primeiros são todos.
 */
export async function apiListAll<T>(path: string): Promise<T[]> {
  const url = new URL(path, window.location.origin)
  url.searchParams.set('page', '1')
  url.searchParams.set('per_page', '100')
  const request = () => api<PaginatedResponse<T> | T[]>(url.pathname + url.search)
  const first = await request()
  if (Array.isArray(first)) return first
  if (!first || !Array.isArray(first.items) || !Number.isInteger(first.pages) || first.pages < 0) {
    throw new Error('Formato inválido na resposta paginada da API.')
  }
  const rows = [...first.items]
  for (let page = 2; page <= first.pages; page += 1) {
    url.searchParams.set('page', String(page))
    const result = await request()
    if (Array.isArray(result) || !result || !Array.isArray(result.items) || result.page !== page) {
      throw new Error(`Resposta inválida ao consultar a página ${page}.`)
    }
    rows.push(...result.items)
  }
  return rows
}
