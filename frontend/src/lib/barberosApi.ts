// Barberos, sus servicios y el portafolio público contra el backend real.
// GET /api/v1/barbers y /api/v1/portfolio son públicos (los usa la reserva);
// asignar servicios a un barbero exige un administrador autenticado.
import { useAuthStore } from '@/stores/useAuthStore'

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:5000'

/** Error con un mensaje apto para mostrar al usuario. */
export class BarberosError extends Error {}

export interface BarberoApi {
  id: number
  name: string
  /** Ids de los servicios activos que realiza. */
  servicios: number[]
}

export interface FotoPublicaApi {
  id: number
  image_url: string
  nota: string
  created_at: string
  servicio: {
    id: number
    name: string
    price: string
    duration_minutes: number
    description: string
  }
  barbero: { id: number; name: string }
}

function autorizacion(): Record<string, string> {
  const token = useAuthStore.getState().accessToken
  return token ? { Authorization: `Bearer ${token}` } : {}
}

async function pedir(url: string, init?: RequestInit): Promise<Response> {
  try {
    return await fetch(url, init)
  } catch {
    throw new BarberosError('No se pudo conectar con el servidor.')
  }
}

/** Barberos de la barbería; con `servicioId`, solo los que hacen ese servicio. */
export async function listarBarberosApi(servicioId?: number): Promise<BarberoApi[]> {
  const filtro = servicioId === undefined ? '' : `?service=${servicioId}`
  const response = await pedir(`${API_URL}/api/v1/barbers${filtro}`)
  if (!response.ok) throw new BarberosError('No se pudieron cargar los barberos.')
  return (await response.json()) as BarberoApi[]
}

/** El admin define qué servicios realiza un barbero. */
export async function asignarServiciosApi(
  barberoId: number,
  servicios: number[],
): Promise<BarberoApi> {
  const response = await pedir(`${API_URL}/api/v1/barbers/${barberoId}/services`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json', ...autorizacion() },
    body: JSON.stringify({ servicios }),
  })
  if (response.status === 401 || response.status === 403) {
    throw new BarberosError('Tu sesión no permite asignar servicios.')
  }
  if (!response.ok) throw new BarberosError('No se pudieron guardar los servicios.')
  return (await response.json()) as BarberoApi
}

/** Trabajos que ve el cliente, filtrables por barbero y por servicio. */
export async function listarPortafolioPublicoApi(filtros: {
  barberoId?: number
  servicioId?: number
}): Promise<FotoPublicaApi[]> {
  const params = new URLSearchParams()
  if (filtros.barberoId !== undefined) params.set('barber', String(filtros.barberoId))
  if (filtros.servicioId !== undefined)
    params.set('service', String(filtros.servicioId))
  const consulta = params.size ? `?${params}` : ''
  const response = await pedir(`${API_URL}/api/v1/portfolio${consulta}`)
  if (!response.ok) throw new BarberosError('No se pudieron cargar los trabajos.')
  return (await response.json()) as FotoPublicaApi[]
}
