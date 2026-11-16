import { useAuthStore } from '@/stores/useAuthStore'
import { listarBarberosApi } from './barberosApi'
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
  /** Días que atiende (0 lunes … 6 domingo), del horario que configuró el admin. */
  diasLaborales?: number[]
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
  /** Último instante (ISO) en que aún se puede reprogramar; lo calcula el backend. */
  reprogramarAntes?: string
  /** Horas de antelación mínima que exige el backend para reprogramar. */
  horasAntelacion?: number
}

export interface NuevaCita {
  servicioId: number
  barberoId: number
  /** Barbero elegido, para el resumen de la cita confirmada. */
  barbero?: Barbero
  inicio: string
  contactoNombre?: string
  contactoCelular?: string
}

// Rol y calificación siguen viniendo del prototipo de Figma (Prototipo interactivo
// BarberFlow OS): el backend aún no los guarda (gestión de barberos, HU-08).
const EXTRAS_PROTOTIPO: Record<string, Pick<Barbero, 'rol' | 'calificacion'>> = {
  Thiago: { rol: 'Master barber', calificacion: 4.9 },
  Andrés: { rol: 'Barber senior', calificacion: 4.8 },
  Nicolás: { rol: 'Barber', calificacion: 4.7 },
}

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

/**
 * Llama a la API enviando el token si hay sesión. Si el token venció (401) se
 * cierra la sesión y se repite como visitante: reservar no exige cuenta.
 */
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

/** Barberos que realizan el servicio (los asigna el admin); sin servicio, todos. */
export async function listarBarberos(servicioId?: number): Promise<Barbero[]> {
  const barberos = await listarBarberosApi(servicioId)
  return barberos.map((b) => ({
    id: b.id,
    nombre: b.name,
    diasLaborales: b.working_days,
    ...(EXTRAS_PROTOTIPO[b.name] ?? { rol: 'Barbero', calificacion: 0 }),
  }))
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
  barber?: number
  service?: number
}

export async function crearCita(datos: NuevaCita): Promise<CitaConfirmada> {
  const servicio = (await listarServicios()).find((s) => s.id === datos.servicioId)
  if (!servicio) throw new ReservaError('No se pudo registrar la reserva.')
  // El wizard ya conoce al barbero elegido; sin él se arma uno mínimo con el id.
  const barbero: Barbero = datos.barbero ?? {
    id: datos.barberoId,
    nombre: 'Barbero',
    rol: 'Barbero',
    calificacion: 0,
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

// ======================================================================
// HU-03: listar, cancelar y reprogramar citas del cliente
// ======================================================================

export interface CitaPerfilApi {
  id: number
  status: string
  start_at: string
  price: string
  service: {
    id: number
    name: string
    price: number
    duration_minutes: number
    description?: string
  }
  barber: {
    id: number
    name: string
    rol?: string
    calificacion?: number
    /** Días que atiende (0 lunes … 6 domingo). */
    working_days?: number[]
  }
  /** Último instante en que aún se puede reprogramar (calculado por el backend). */
  reschedule_deadline?: string
  min_notice_hours?: number
}

/** Mensaje del backend (`detail`) si viene en la respuesta; si no, el de respaldo. */
async function mensajeDe(response: Response, respaldo: string): Promise<string> {
  try {
    const cuerpo = (await response.json()) as { detail?: unknown }
    return typeof cuerpo.detail === 'string' ? cuerpo.detail : respaldo
  } catch {
    return respaldo
  }
}

/**
 * Lista las citas del usuario autenticado (GET /api/v1/appointments/).
 *
 * PENDIENTE de backend: ese listado aún no existe en develop (SCRUM-52 solo
 * agrega cancelar y reprogramar). El contrato de `CitaPerfilApi` es el que
 * este cliente espera; hay que acordarlo con quien implemente el endpoint.
 */
export async function listarMisCitasApi(): Promise<CitaConfirmada[]> {
  let response: Response
  try {
    response = await pedir(`${API_URL}/api/v1/appointments/`)
  } catch {
    throw new ReservaError('No se pudo conectar con el servidor.')
  }
  if (!response.ok) throw new ReservaError('No se pudieron cargar tus citas.')

  const data = (await response.json()) as CitaPerfilApi[]
  return data.map((cita) => ({
    id: cita.id,
    estado: cita.status,
    servicio: {
      id: cita.service.id,
      nombre: cita.service.name,
      precio: Number(cita.service.price),
      duracionMin: cita.service.duration_minutes,
      descripcion: cita.service.description,
    },
    barbero: {
      id: cita.barber.id,
      nombre: cita.barber.name,
      rol: cita.barber.rol ?? 'Barbero',
      calificacion: cita.barber.calificacion ?? 0,
      diasLaborales: cita.barber.working_days,
    },
    inicio: aIsoColombia(cita.start_at),
    total: Number(cita.price),
    reprogramarAntes: cita.reschedule_deadline,
    horasAntelacion: cita.min_notice_hours,
  }))
}

/**
 * Cancela una cita (POST /api/v1/appointments/{id}/cancel).
 *
 * Cancelar siempre se permite al propietario. Con la antelación mínima o menos
 * la cancelación se registra como tardía: `tardia` es true en ese caso.
 */
export async function cancelarCitaApi(
  citaId: number | string,
): Promise<{ tardia: boolean }> {
  let response: Response
  try {
    response = await pedir(`${API_URL}/api/v1/appointments/${citaId}/cancel`, {
      method: 'POST',
    })
  } catch {
    throw new ReservaError('No se pudo conectar con el servidor.')
  }
  if (response.status === 401) {
    throw new ReservaError('Inicia sesión para cancelar tu cita.')
  }
  if (!response.ok) {
    throw new ReservaError(
      await mensajeDe(response, 'No se pudo cancelar la cita. Intenta de nuevo.'),
    )
  }

  const cita = (await response.json()) as { late_cancellation?: boolean }
  return { tardia: cita.late_cancellation === true }
}

/**
 * Reprograma una cita (POST /api/v1/appointments/{id}/reschedule).
 *
 * Mantiene barbero y servicio. El backend exige MÁS de la antelación mínima
 * sobre la hora original y una franja libre; `nuevoInicio` debe llevar zona.
 */
export async function reprogramarCitaApi(
  cita: CitaConfirmada,
  nuevoInicio: string,
): Promise<CitaConfirmada> {
  let response: Response
  try {
    response = await pedir(`${API_URL}/api/v1/appointments/${cita.id}/reschedule`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ start_at: nuevoInicio }),
    })
  } catch {
    throw new ReservaError('No se pudo conectar con el servidor.')
  }
  if (response.status === 401) {
    throw new ReservaError('Inicia sesión para reprogramar tu cita.')
  }
  if (!response.ok) {
    throw new ReservaError(
      await mensajeDe(
        response,
        response.status === 409
          ? 'Ese horario ya no está disponible. Elige otro.'
          : 'No se pudo reprogramar la cita. Intenta de nuevo.',
      ),
    )
  }

  const actualizada = (await response.json()) as CitaApi
  // La nueva hora tiene su propio límite: la misma antelación antes de ella.
  const reprogramarAntes = cita.horasAntelacion
    ? new Date(
        new Date(actualizada.start_at).getTime() - cita.horasAntelacion * 3_600_000,
      ).toISOString()
    : undefined
  return {
    ...cita,
    estado: actualizada.status,
    inicio: aIsoColombia(actualizada.start_at),
    total: Number(actualizada.price),
    reprogramarAntes,
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
