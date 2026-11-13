// Capa de datos del wizard de reserva (SCRUM-44).
// Servicios, franjas (GET /api/v1/availability) y la cita (POST /api/v1/appointments)
// vienen del backend y no exigen cuenta: con sesión la cita queda a su nombre;
// sin ella se envían el nombre y el celular de contacto. Los barberos siguen siendo los tres de la demo:
// la gestión de barberos y de sus horarios (HU-08) es del Sprint 2.

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
  hora: string // HH:mm, 24 h
  disponible: boolean
}

export interface CitaConfirmada {
  id: number
  estado: string
  servicio: Servicio
  barbero: Barbero
  inicio: string // ISO 8601 con zona horaria
  total: number
}

export interface NuevaCita {
  servicioId: number
  barberoId: number
  inicio: string
  /** Contacto del visitante sin cuenta (con sesión no hace falta). */
  contactoNombre?: string
  contactoCelular?: string
}

// Datos tomados del prototipo de Figma (Prototipo interactivo BarberFlow OS).
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

/** Instante en hora de Colombia como 'YYYY-MM-DDTHH:mm:00-05:00' (sin horario de verano). */
const aIsoColombia = (iso: string) => {
  const d = new Date(iso)
  return `${fechaLocalBarberia.format(d)}T${horaLocal.format(d)}:00-05:00`
}

const pausa = (ms = 150) => new Promise<void>((r) => setTimeout(r, ms))

/**
 * Llama a la API enviando el token si hay sesión. Si el token venció (401) se
 * cierra la sesión y se repite como visitante: reservar no exige cuenta.
 */
async function pedir(url: string, init: RequestInit = {}): Promise<Response> {
  const { accessToken, clearSession } = useAuthStore.getState()
  const conToken = accessToken
    ? { ...init, headers: { ...init.headers, Authorization: `Bearer ${accessToken}` } }
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

/**
 * Franjas libres del barbero ese día (GET /api/v1/availability), según el horario
 * laboral y el descanso configurados y las citas ya tomadas. El backend solo ofrece
 * bloques de 30 o 60 min: se usa el menor que cubre la duración del servicio.
 * Solo se devuelven las libres y futuras; las ocupadas simplemente no aparecen.
 */
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
  if (!response.ok) throw new ReservaError('No se pudieron cargar los horarios.')

  const { available_slots } = (await response.json()) as { available_slots: SlotApi[] }
  const ahora = Date.now()
  return available_slots
    .filter((s) => new Date(s.start_at).getTime() > ahora)
    .map((s) => ({ hora: horaLocal.format(new Date(s.start_at)), disponible: true }))
}

interface CitaApi {
  id: number
  status: string
  start_at: string
  price: string
  barber?: number
  service?: number
}

/** Crea la cita (POST /api/v1/appointments), con sesión o como visitante. */
export async function crearCita(datos: NuevaCita): Promise<CitaConfirmada> {
  const servicio = (await listarServicios()).find((s) => s.id === datos.servicioId)
  const barbero = BARBEROS.find((b) => b.id === datos.barberoId)
  if (!servicio || !barbero) throw new ReservaError('No se pudo registrar la reserva.')

  let response: Response
  try {
    response = await pedir(`${API_URL}/api/v1/appointments`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        barber: datos.barberoId,
        service: datos.servicioId,
        start_at: datos.inicio,
        ...(datos.contactoNombre && { contact_name: datos.contactoNombre }),
        ...(datos.contactoCelular && { contact_phone: datos.contactoCelular }),
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
    // La API responde en UTC: la pantalla muestra la hora de la barbería.
    inicio: aIsoColombia(cita.start_at),
    total: Number(cita.price),
  }
}

// ======================================================================
// AMPLIACIÓN PARA HU-03 (SUB-03-B): Listar, Cancelar y Reprogramar citas
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
  }
}

/** Lista las citas del usuario autenticado (GET /api/v1/appointments/). */
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
      rol: cita.barber.rol ?? 'Barber',
      calificacion: cita.barber.calificacion ?? 4.8,
    },
    inicio: aIsoColombia(cita.start_at),
    total: Number(cita.price),
  }))
}

/** Cancela una cita (DELETE /api/v1/appointments/{id}/). */
export async function cancelarCitaApi(citaId: number | string): Promise<void> {
  let response: Response
  try {
    response = await pedir(`${API_URL}/api/v1/appointments/${citaId}/`, {
      method: 'DELETE',
    })
  } catch {
    throw new ReservaError('No se pudo conectar con el servidor.')
  }
  if (!response.ok) {
    throw new ReservaError(
      'No se pudo cancelar la cita. Verifica que falten más de 12 horas.',
    )
  }
}

/** Reprograma una cita existente (PATCH /api/v1/appointments/{id}/). */
export async function reprogramarCitaApi(
  citaId: number | string,
  nuevoInicio: string,
): Promise<CitaConfirmada> {
  let response: Response
  try {
    response = await pedir(`${API_URL}/api/v1/appointments/${citaId}/`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ start_at: nuevoInicio }),
    })
  } catch {
    throw new ReservaError('No se pudo conectar con el servidor.')
  }
  if (response.status === 409) {
    throw new ReservaError('Ese horario ya no está disponible. Elige otro.')
  }
  if (!response.ok) {
    throw new ReservaError(
      'No se pudo reprogramar la cita. Verifica la antelación mínima de 12 horas.',
    )
  }

  const cita = (await response.json()) as CitaApi
  const serviciosDisponibles = await listarServicios()
  const servicio =
    serviciosDisponibles.find((s) => s.id === cita.service) ?? serviciosDisponibles[0]
  const barbero = BARBEROS.find((b) => b.id === cita.barber) ?? BARBEROS[0]

  return {
    id: cita.id,
    estado: cita.status,
    servicio,
    barbero,
    inicio: aIsoColombia(cita.start_at),
    total: Number(cita.price),
  }
}
