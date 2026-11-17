// Saludo según la hora del día para dar la bienvenida al usuario.

export type PeriodoDelDia = 'manana' | 'tarde' | 'noche'

/** Mañana de 5:00 a 11:59, tarde de 12:00 a 18:59 y noche el resto. */
export function periodoSegunHora(hora: number): PeriodoDelDia {
  if (hora >= 5 && hora < 12) return 'manana'
  if (hora >= 12 && hora < 19) return 'tarde'
  return 'noche'
}

const SALUDOS: Record<PeriodoDelDia, string> = {
  manana: 'Buenos días',
  tarde: 'Buenas tardes',
  noche: 'Buenas noches',
}

export const saludoSegunHora = (hora: number): string => SALUDOS[periodoSegunHora(hora)]

/** Primera palabra del nombre completo ('' si no hay nombre). */
export function primerNombre(nombreCompleto: string | undefined): string {
  return nombreCompleto?.trim().split(/\s+/)[0] ?? ''
}
