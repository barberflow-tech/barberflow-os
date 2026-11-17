// Horario semanal de un barbero contra el backend real (HU-08).
// GET/PUT /api/v1/barbers/{id}/schedule exigen un administrador autenticado.
import { MENSAJE_SIN_CONEXION } from './mensajes'
import { useAuthStore } from '@/stores/useAuthStore'

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:5000'

/** Error con un mensaje apto para mostrar al usuario. */
export class HorariosError extends Error {}

/** Cita futura que el cambio de horario dejaría fuera de la jornada. */
export interface CitaEnConflicto {
  appointment: number
  start_at: string
  reason: string
}

/** 409: guardar el horario afecta citas futuras; trae cuáles son. */
export class HorarioConflictoError extends HorariosError {
  conflictos: CitaEnConflicto[]

  constructor(mensaje: string, conflictos: CitaEnConflicto[]) {
    super(mensaje)
    this.conflictos = conflictos
  }
}

/** Turno de un día. `weekday`: 0 lunes … 6 domingo; horas "HH:MM". */
export interface HorarioDia {
  weekday: number
  open_time: string
  close_time: string
  break_start: string | null
  break_duration_minutes: number | null
}

export interface HorarioSemanal {
  barber: number
  name: string
  timezone: string
  days: HorarioDia[]
  updated_at: string | null
}

function autorizacion(): Record<string, string> {
  const token = useAuthStore.getState().accessToken
  return token ? { Authorization: `Bearer ${token}` } : {}
}

async function pedir(url: string, init: RequestInit = {}): Promise<Response> {
  try {
    return await fetch(url, {
      ...init,
      headers: {
        'Content-Type': 'application/json',
        ...autorizacion(),
      },
    })
  } catch {
    throw new HorariosError(MENSAJE_SIN_CONEXION)
  }
}

async function leer(response: Response, mensajeError: string): Promise<HorarioSemanal> {
  if (response.status === 401 || response.status === 403) {
    throw new HorariosError('Tu sesión no permite configurar horarios.')
  }
  if (response.status === 404) {
    throw new HorariosError('Ese barbero no existe o ya no está disponible.')
  }
  if (response.status === 409) {
    const cuerpo = (await response.json().catch(() => ({}))) as {
      detail?: string
      conflicts?: CitaEnConflicto[]
    }
    throw new HorarioConflictoError(
      cuerpo.detail ?? 'El cambio afecta citas futuras.',
      cuerpo.conflicts ?? [],
    )
  }
  if (response.status === 400) {
    throw new HorariosError('Revisa los horarios: algún turno o descanso no es válido.')
  }
  if (!response.ok) throw new HorariosError(mensajeError)
  return (await response.json()) as HorarioSemanal
}

/** La semana completa del barbero; los días sin turno no vienen en `days`. */
export async function obtenerHorarioApi(barberoId: number): Promise<HorarioSemanal> {
  const response = await pedir(`${API_URL}/api/v1/barbers/${barberoId}/schedule`)
  return leer(response, 'No se pudo cargar el horario.')
}

/** Reemplaza la semana: los días omitidos quedan sin trabajo. */
export async function guardarHorarioApi(
  barberoId: number,
  days: HorarioDia[],
): Promise<HorarioSemanal> {
  const response = await pedir(`${API_URL}/api/v1/barbers/${barberoId}/schedule`, {
    method: 'PUT',
    body: JSON.stringify({ days }),
  })
  return leer(response, 'No se pudo guardar el horario.')
}
