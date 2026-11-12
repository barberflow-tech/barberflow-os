import { useAuthStore } from '@/stores/useAuthStore'
import { listarServiciosApi } from './catalogoApi'

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:5000'

/** Error con un mensaje apto para mostrar al usuario. */
export class ReservaError extends Error {}

export interface Servicio {
  id: number
  nombre: string
  precio: number
  duracionMin: number
  descripcion?: string
}

export interface Barbero {
  id: number
  nombre: string
  rol: string
  calificacion: number
}

export interface FranjaHoraria {
  hora: string
  disponible: boolean
}

export interface CitaConfirmada {
  id: number
  estado: string
  servicio: Servicio
  barbero: Barbero
  inicio: string
  total: number
}

export interface NuevaCita {
  servicioId: number
  barberoId: number
  inicio: string
  contactoNombre?: string
  contactoCelular?: string
}

const BARBEROS: Barbero[] = [
  { id: 1, nombre: 'Thiago', rol: 'Master barber', calificacion: 4.9 },
  { id: 2, nombre: 'Andrés', rol: 'Barber senior', calificacion: 4.8 },
  { id: 3, nombre: 'Nicolás', rol: 'Barber', calificacion: 4.7 },
]

const ZONA_BARBERIA = 'America/Bogota'

const horaLocal = new Intl.DateTimeFormat('en-GB', {
  timeZone: ZONA_BARBERIA,
  hour: '2-digit',
  minute: '2-digit',
  hourCycle: 'h23',
})

const fechaLocalBarberia = new Intl.DateTimeFormat('en-CA', {
  timeZone: ZONA_BARBERIA,
  year: 'numeric',
  month: '2-digit',
  day: '2-digit',
})

const aIsoColombia = (iso: string) => {
  const d = new Date(iso)
  return `${fechaLocalBarberia.format(d)}T${horaLocal.format(d)}:00-05:00`
}

const pausa = (ms = 150) => new Promise<void>((r) => setTimeout(r, ms))

async function pedir(url: string, init: RequestInit = {}): Promise<Response> {
  const { accessToken, clearSession } = useAuthStore.getState()

  const conToken = accessToken
    ? {
        ...init,
        headers: {
          ...init.headers,
          Authorization: `Bearer ${accessToken}`,
        },
      }
    : init

  const response = await fetch(url, conToken)

  if (response.status === 401 && accessToken) {
    clearSession()
    return fetch(url, init)
  }

  return response
}

export async function listarServicios(): Promise<Servicio[]> {
  const servicios = await listarServiciosApi()

  return servicios
    .filter((s) => s.is_active)
    .map((s) => ({
      id: s.id,
      nombre: s.name,
      precio: s.price,
      duracionMin: s.duration_minutes,
      descripcion: s.description,
    }))
}

export async function listarBarberos(): Promise<Barbero[]> {
  await pausa()
  return BARBEROS
}

interface SlotApi {
  start_at: string
  end_at: string
}

export async function listarFranjas(
  barberoId: number,
  fecha: string,
  duracionServicioMin = 30,
): Promise<FranjaHoraria[]> {
  const slot = duracionServicioMin <= 30 ? 30 : 60

  let response: Response

  try {
    response = await pedir(
      `${API_URL}/api/v1/availability?barber=${barberoId}&date=${fecha}&slot_duration=${slot}`,
    )
  } catch {
    throw new ReservaError('No se pudo conectar con el servidor.')
  }

  if (response.status === 404) {
    throw new ReservaError('Ese barbero no está disponible. Elige otro.')
  }

  if (!response.ok) {
    throw new ReservaError('No se pudieron cargar los horarios.')
  }

  const { available_slots } = (await response.json()) as {
    available_slots: SlotApi[]
  }

  const ahora = Date.now()

  return available_slots
    .filter((s) => new Date(s.start_at).getTime() > ahora)
    .map((s) => ({
      hora: horaLocal.format(new Date(s.start_at)),
      disponible: true,
    }))
}

interface CitaApi {
  id: number
  status: string
  start_at: string
  price: string
}

export async function crearCita(datos: NuevaCita): Promise<CitaConfirmada> {
  const servicio = (await listarServicios()).find((s) => s.id === datos.servicioId)

  const barbero = BARBEROS.find((b) => b.id === datos.barberoId)

  if (!servicio || !barbero) {
    throw new ReservaError('No se pudo registrar la reserva.')
  }

  let response: Response

  try {
    response = await pedir(`${API_URL}/api/v1/appointments`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        barber: datos.barberoId,
        service: datos.servicioId,
        start_at: datos.inicio,
        ...(datos.contactoNombre && {
          contact_name: datos.contactoNombre,
        }),
        ...(datos.contactoCelular && {
          contact_phone: datos.contactoCelular,
        }),
      }),
    })
  } catch {
    throw new ReservaError('No se pudo conectar con el servidor.')
  }

  if (response.status === 429) {
    throw new ReservaError(
      'Demasiados intentos. Espera un momento e inténtalo de nuevo.',
    )
  }

  if (response.status === 403) {
    throw new ReservaError('Tu cuenta no puede reservar citas.')
  }

  if (response.status === 409) {
    throw new ReservaError('Ese horario acaba de ocupar otra persona. Elige otro.')
  }

  if (!response.ok) {
    throw new ReservaError('No se pudo registrar la reserva. Inténtalo de nuevo.')
  }

  const cita = (await response.json()) as CitaApi

  return {
    id: cita.id,
    estado: cita.status,
    servicio,
    barbero,
    inicio: aIsoColombia(cita.start_at),
    total: Number(cita.price),
  }
}

// ======================================================
// GESTIÓN DE BLOQUEOS (Conectado al Backend)
// ======================================================

export interface Bloqueo {
  id: string | number
  barberoId: string | number
  fecha: string
  horaInicio: string
  horaFin: string
  motivo: string
}

export const obtenerBloqueosApi = async (): Promise<Bloqueo[]> => {
  const response = await pedir(`${API_URL}/api/v1/bloqueos`)
  if (!response.ok) throw new ReservaError('Error al cargar los bloqueos.')
  return response.json()
}

export const crearBloqueoApi = async (nuevo: Omit<Bloqueo, 'id'>): Promise<Bloqueo> => {
  const response = await pedir(`${API_URL}/api/v1/bloqueos`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(nuevo),
  })
  if (!response.ok) throw new ReservaError('Error al crear el bloqueo.')
  return response.json()
}

export const actualizarBloqueoApi = async (
  id: string,
  cambios: Omit<Bloqueo, 'id'>,
): Promise<Bloqueo> => {
  const response = await pedir(`${API_URL}/api/v1/bloqueos/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(cambios),
  })
  if (!response.ok)
    throw new ReservaError('No se encontró el bloqueo que deseas editar.')
  return response.json()
}

export const eliminarBloqueoApi = async (id: string | number): Promise<void> => {
  const response = await pedir(`${API_URL}/api/v1/bloqueos/${id}`, {
    method: 'DELETE',
  })
  if (!response.ok) throw new ReservaError('Error al eliminar el bloqueo.')
}
