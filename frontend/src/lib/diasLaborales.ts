// Días en que un barbero atiende, según el horario que configuró el administrador
// (HU-08). El backend los expone como `working_days`: 0 lunes … 6 domingo.
import { aIso, fechaLocal } from '@/components/booking/wizard/formato'

/** Día de la semana de 'YYYY-MM-DD' con la numeración del backend (0 lunes … 6 domingo). */
export const diaSemana = (fecha: string): number => (fechaLocal(fecha).getDay() + 6) % 7

/**
 * ¿Atiende ese día? Sin dato del horario (`undefined`) se asume que sí: el
 * backend igual rechaza o no ofrece franjas en un día cerrado.
 */
export const atiendeEl = (dias: number[] | undefined, fecha: string): boolean =>
  !dias || dias.includes(diaSemana(fecha))

/** Suma días a 'YYYY-MM-DD' (sin depender de la zona horaria del navegador). */
export function sumarDias(fecha: string, cantidad: number): string {
  const d = fechaLocal(fecha)
  d.setDate(d.getDate() + cantidad)
  return aIso(d)
}

/**
 * Primeros `cantidad` días en que se atiende, contando desde `desde` (incluido).
 * Mira como máximo `horizonte` días hacia adelante para no ciclar si el barbero
 * no tiene ningún día configurado.
 */
export function proximosDiasLaborales(
  desde: string,
  dias: number[] | undefined,
  cantidad: number,
  horizonte = 60,
): string[] {
  const resultado: string[] = []
  for (let i = 0; i < horizonte && resultado.length < cantidad; i++) {
    const fecha = sumarDias(desde, i)
    if (atiendeEl(dias, fecha)) resultado.push(fecha)
  }
  return resultado
}

/** Primer día en que se atiende desde `desde`, o `null` si no atiende ninguno. */
export const primerDiaLaboral = (
  desde: string,
  dias: number[] | undefined,
): string | null => proximosDiasLaborales(desde, dias, 1)[0] ?? null
