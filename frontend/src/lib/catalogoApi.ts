// Catálogo de servicios contra el backend real (GET /api/v1/services, SCRUM-37).
// La lectura es pública: no necesita sesión. Crear, editar y borrar exigen un
// administrador autenticado (is_staff): el access token viaja en Authorization.
import { useAuthStore } from '@/stores/useAuthStore'

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:5000'

export interface ServicioApi {
  id: number
  name: string
  price: number
  duration_minutes: number
  description: string
  is_active: boolean
}

/** Error con un mensaje apto para mostrar al usuario. */
export class CatalogoError extends Error {}

interface ServicioCrudo {
  id: number
  name: string
  price: string | number
  duration_minutes: number
  description?: string
  is_active: boolean
}

function aServicio(s: ServicioCrudo): ServicioApi {
  // DRF serializa los decimales como texto ("35000.00").
  return { ...s, price: Number(s.price), description: s.description ?? '' }
}

function autorizacion(): Record<string, string> {
  const token = useAuthStore.getState().accessToken
  return token ? { Authorization: `Bearer ${token}` } : {}
}

/** Entrada de crear/editar: lo que el backend guarda de un servicio. */
export interface ServicioEntrada {
  name: string
  price: number
  duration_minutes: number
  description: string
  is_active: boolean
}

/**
 * Lista el catálogo. Con `incluirInactivos` (solo el panel admin) se envía la sesión y
 * un administrador recibe también los servicios desactivados; el público no los ve.
 */
export async function listarServiciosApi(
  opciones: { incluirInactivos?: boolean } = {},
): Promise<ServicioApi[]> {
  let response: Response
  try {
    const url = `${API_URL}/api/v1/services`
    response = opciones.incluirInactivos
      ? await fetch(url, { headers: autorizacion() })
      : await fetch(url)
  } catch {
    throw new CatalogoError('No se pudo conectar con el servidor.')
  }
  if (!response.ok) {
    throw new CatalogoError('No se pudieron cargar los servicios.')
  }
  return ((await response.json()) as ServicioCrudo[]).map(aServicio)
}

/** Primer mensaje de validación que devuelve DRF ({campo: ["mensaje"]}). */
function mensajeDeValidacion(cuerpo: unknown): string | null {
  if (cuerpo && typeof cuerpo === 'object') {
    for (const [campo, valor] of Object.entries(cuerpo)) {
      const mensaje = Array.isArray(valor) ? valor[0] : valor
      if (typeof mensaje === 'string') return `${campo}: ${mensaje}`
    }
  }
  return null
}

async function enviar(
  metodo: 'POST' | 'PUT' | 'DELETE',
  ruta: string,
  cuerpo?: ServicioEntrada,
): Promise<Response> {
  let response: Response
  try {
    response = await fetch(`${API_URL}/api/v1/services${ruta}`, {
      method: metodo,
      headers: {
        ...autorizacion(),
        ...(cuerpo ? { 'Content-Type': 'application/json' } : {}),
      },
      body: cuerpo ? JSON.stringify(cuerpo) : undefined,
    })
  } catch {
    throw new CatalogoError('No se pudo conectar con el servidor.')
  }
  if (response.ok) return response

  if (response.status === 401) {
    throw new CatalogoError('Tu sesión expiró. Inicia sesión de nuevo.')
  }
  if (response.status === 403) {
    throw new CatalogoError('Solo un administrador puede modificar el catálogo.')
  }
  if (response.status === 404) {
    throw new CatalogoError('El servicio ya no existe. Recarga la página.')
  }
  const detalle =
    response.status === 400
      ? mensajeDeValidacion(await response.json().catch(() => null))
      : null
  throw new CatalogoError(
    detalle ?? 'No se pudo guardar el servicio. Inténtalo de nuevo.',
  )
}

export async function crearServicioApi(datos: ServicioEntrada): Promise<ServicioApi> {
  const response = await enviar('POST', '', datos)
  return aServicio((await response.json()) as ServicioCrudo)
}

export async function actualizarServicioApi(
  id: number | string,
  datos: ServicioEntrada,
): Promise<ServicioApi> {
  const response = await enviar('PUT', `/${id}`, datos)
  return aServicio((await response.json()) as ServicioCrudo)
}

/** Desactiva el servicio (borrado lógico en el backend). */
export async function eliminarServicioApi(id: number | string): Promise<void> {
  await enviar('DELETE', `/${id}`)
}
