// Catálogo de servicios contra el backend real (GET /api/v1/services, SCRUM-37).
// La lectura es pública: no necesita sesión. Crear, editar y borrar exigen un
// administrador autenticado y se conectarán cuando exista la auth (SCRUM-29).

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

export async function listarServiciosApi(): Promise<ServicioApi[]> {
  let response: Response
  try {
    response = await fetch(`${API_URL}/api/v1/services`)
  } catch {
    throw new CatalogoError('No se pudo conectar con el servidor.')
  }
  if (!response.ok) {
    throw new CatalogoError('No se pudieron cargar los servicios.')
  }

  const datos = (await response.json()) as ServicioCrudo[]
  // DRF serializa los decimales como texto ("35000.00").
  return datos.map((s) => ({
    ...s,
    price: Number(s.price),
    description: s.description ?? '',
  }))
}
