// Reglas de antelación de HU-03 vistas desde el perfil del cliente.
//
// El número de horas NO vive aquí: lo define el backend y llega con cada cita
// (`reprogramarAntes` y `horasAntelacion`). Estas funciones solo lo interpretan,
// así cambiar la política no exige tocar el frontend. El backend decide siempre:
// si algo de esto se desactualiza, la API igual rechaza lo que no corresponde.
import type { CitaConfirmada } from '@/lib/reservaApi'

/** "1 hora" / "2 horas"; sin dato, un texto genérico. */
export function textoHoras(horas?: number): string {
  if (!horas) return 'la antelación mínima'
  return horas === 1 ? '1 hora' : `${horas} horas`
}

/**
 * ¿Todavía se puede reprogramar? Sin dato del límite (respuesta antigua) se
 * deja intentar y el backend responde.
 */
export function puedeReprogramar(cita: CitaConfirmada, ahora: number): boolean {
  if (!cita.reprogramarAntes) return true
  return ahora < Date.parse(cita.reprogramarAntes)
}

/**
 * ¿Cancelar ahora se registraría como tardía? Es la otra cara de reprogramar:
 * pasada la hora límite, cancelar deja de ser «a tiempo».
 */
export function cancelacionSeraTardia(cita: CitaConfirmada, ahora: number): boolean {
  return !puedeReprogramar(cita, ahora) && !!cita.reprogramarAntes
}
