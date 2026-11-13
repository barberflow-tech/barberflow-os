// Asignación de roles por el administrador (SCRUM-70 / HU-09).
// GET /api/v1/users lista los usuarios de su barbería; con ?email= busca por correo
// exacto (también clientes sin barbería). PATCH /api/v1/users/<id>/role cambia el rol.
import type { Role } from '@/stores/useAuthStore'
import { useAuthStore } from '@/stores/useAuthStore'

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:5000'

export interface UsuarioConRol {
  id: number
  email: string
  full_name: string
  role: Role
  /** true si ya pertenece a la barbería del administrador. */
  en_barberia: boolean
}

/** Error con un mensaje apto para mostrar al usuario. */
export class UsuariosError extends Error {}

function autorizacion(): Record<string, string> {
  const token = useAuthStore.getState().accessToken
  return token ? { Authorization: `Bearer ${token}` } : {}
}

async function pedir(ruta: string, init: RequestInit = {}): Promise<Response> {
  let response: Response
  try {
    response = await fetch(`${API_URL}/api/v1/users${ruta}`, {
      ...init,
      headers: { ...autorizacion(), ...(init.headers ?? {}) },
    })
  } catch {
    throw new UsuariosError('No se pudo conectar con el servidor.')
  }
  if (response.ok) return response

  const cuerpo = (await response.json().catch(() => null)) as {
    detail?: unknown
    role?: unknown
  } | null
  const detalle = typeof cuerpo?.detail === 'string' ? cuerpo.detail : null
  if (response.status === 401) {
    throw new UsuariosError('Tu sesión expiró. Inicia sesión de nuevo.')
  }
  if (response.status === 403) {
    throw new UsuariosError('Solo un administrador puede cambiar roles.')
  }
  if (response.status === 404) {
    throw new UsuariosError('El usuario ya no existe o no pertenece a tu barbería.')
  }
  if ((response.status === 400 || response.status === 409) && detalle) {
    throw new UsuariosError(detalle)
  }
  if (response.status === 400 && Array.isArray(cuerpo?.role)) {
    throw new UsuariosError('Elige un rol válido.')
  }
  throw new UsuariosError('No se pudo completar la operación. Inténtalo de nuevo.')
}

/** Usuarios de la barbería del admin; con `email`, solo la coincidencia exacta. */
export async function listarUsuariosApi(email?: string): Promise<UsuarioConRol[]> {
  const ruta = email ? `?email=${encodeURIComponent(email)}` : ''
  const response = await pedir(ruta)
  return (await response.json()) as UsuarioConRol[]
}

export async function cambiarRolApi(id: number, role: Role): Promise<UsuarioConRol> {
  const response = await pedir(`/${id}/role`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ role }),
  })
  return (await response.json()) as UsuarioConRol
}
