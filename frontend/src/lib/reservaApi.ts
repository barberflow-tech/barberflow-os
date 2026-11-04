// Capa de datos del wizard de reserva (SCRUM-44).
// Los servicios vienen del backend (GET /api/v1/services). Barberos y franjas siguen
// simulados: aún no existe el GET de barberos y la disponibilidad exige sesión.
// `crearCita` respeta el contrato de POST /api/v1/appointments ({barber, service, start_at}).

import { listarServiciosApi } from './catalogoApi'

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
}

// Datos tomados del prototipo de Figma (Prototipo interactivo BarberFlow OS).
const BARBEROS: Barbero[] = [
  { id: 1, nombre: 'Thiago', rol: 'Master barber', calificacion: 4.9 },
  { id: 2, nombre: 'Andrés', rol: 'Barber senior', calificacion: 4.8 },
  { id: 3, nombre: 'Nicolás', rol: 'Barber', calificacion: 4.7 },
]

const HORAS = ['08:00', '08:45', '10:15', '11:45', '14:00', '16:15', '17:00', '18:30']

const pausa = (ms = 150) => new Promise<void>((r) => setTimeout(r, ms))

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

/** Franjas simuladas: ocupación determinista según barbero y día. */
export async function listarFranjas(
  barberoId: number,
  fecha: string,
): Promise<FranjaHoraria[]> {
  await pausa()
  const semilla = barberoId + Number(fecha.slice(-2))
  return HORAS.map((hora, i) => ({ hora, disponible: (i + semilla) % 3 !== 1 }))
}

export async function crearCita(datos: NuevaCita): Promise<CitaConfirmada> {
  await pausa(300)
  // La cita sigue simulada hasta que exista la auth: busca el servicio en el catálogo real.
  const servicio = (await listarServicios()).find((s) => s.id === datos.servicioId)
  const barbero = BARBEROS.find((b) => b.id === datos.barberoId)
  if (!servicio || !barbero) throw new Error('No se pudo registrar la reserva.')
  return {
    id: Math.floor(Math.random() * 9000) + 1000,
    estado: 'PENDING',
    servicio,
    barbero,
    inicio: datos.inicio,
    total: servicio.precio,
  }
}
