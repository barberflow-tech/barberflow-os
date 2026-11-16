// Portafolio del barbero contra el backend real (SCRUM-35).
// GET/POST /api/v1/barbers/me/portfolio: solo el rol barbero; el access token
// viaja en el encabezado Authorization (vive en memoria, ver useAuthStore).
import { useAuthStore } from '@/stores/useAuthStore'

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:5000'
const URL_PORTAFOLIO = `${API_URL}/api/v1/barbers/me/portfolio`

/** Corte del catálogo vinculado a la foto: lo define el administrador. */
export interface ServicioFotoApi {
  id: number
  name: string
  price: string
  duration_minutes: number
  description: string
}

export interface FotoApi {
  id: number
  servicio: ServicioFotoApi | null
  nota: string
  image_url: string
  original_filename: string
  original_size: number
  optimized_size: number
  created_at: string
}

/** Lo que el barbero indica al subir: el corte (obligatorio) y una nota propia. */
export interface DatosFoto {
  servicioId: number
  nota: string
}

/** Error con un mensaje apto para mostrar al usuario. */
export class PortafolioError extends Error {}

function mensajePorEstado(status: number, detalle?: string): string {
  if (status === 401) return 'Tu sesión expiró. Inicia sesión de nuevo.'
  if (status === 403) return 'Tu cuenta no está vinculada a un barbero.'
  if (status === 400 && detalle) return detalle
  if (status === 502 || status === 503) {
    return 'El almacenamiento no está disponible. Inténtalo más tarde.'
  }
  return 'No se pudo completar la operación. Inténtalo de nuevo.'
}

function autorizacion(): Record<string, string> {
  const token = useAuthStore.getState().accessToken
  return token ? { Authorization: `Bearer ${token}` } : {}
}

export async function listarPortafolio(): Promise<FotoApi[]> {
  let response: Response
  try {
    response = await fetch(URL_PORTAFOLIO, { headers: autorizacion() })
  } catch {
    throw new PortafolioError('No se pudo conectar con el servidor.')
  }
  if (!response.ok) throw new PortafolioError(mensajePorEstado(response.status))
  return (await response.json()) as FotoApi[]
}

/** Sube una foto; usa XHR porque fetch no informa el avance de la subida. */
export function subirFoto(
  archivo: File,
  onProgress: (pct: number) => void,
  datos: DatosFoto,
): Promise<FotoApi> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest()
    xhr.open('POST', URL_PORTAFOLIO)
    for (const [clave, valor] of Object.entries(autorizacion())) {
      xhr.setRequestHeader(clave, valor)
    }
    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable) onProgress((e.loaded / e.total) * 100)
    }
    xhr.onerror = () =>
      reject(new PortafolioError('No se pudo conectar con el servidor.'))
    xhr.onload = () => {
      let cuerpo: unknown
      try {
        cuerpo = JSON.parse(xhr.responseText)
      } catch {
        cuerpo = undefined
      }
      if (xhr.status === 201) {
        onProgress(100)
        resolve(cuerpo as FotoApi)
        return
      }
      const detalle = (cuerpo as { detail?: string } | undefined)?.detail
      reject(new PortafolioError(mensajePorEstado(xhr.status, detalle)))
    }
    const formulario = new FormData()
    formulario.append('image', archivo)
    formulario.append('servicio', String(datos.servicioId))
    if (datos.nota) formulario.append('nota', datos.nota)
    xhr.send(formulario)
  })
}

/** Servicios activos que el admin le asignó al barbero autenticado. */
export async function listarMisServicios(): Promise<ServicioFotoApi[]> {
  let response: Response
  try {
    response = await fetch(`${API_URL}/api/v1/barbers/me/services`, {
      headers: autorizacion(),
    })
  } catch {
    throw new PortafolioError('No se pudo conectar con el servidor.')
  }
  if (!response.ok) throw new PortafolioError(mensajePorEstado(response.status))
  return (await response.json()) as ServicioFotoApi[]
}
