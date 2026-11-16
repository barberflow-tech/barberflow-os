import { useEffect, useState } from 'react'
import { listarFranjas, ReservaError, type FranjaHoraria } from '@/lib/reservaApi'
import { supabase } from '@/lib/supabase'

/** Tabla real de citas (Django). Su publicación en Realtime la crea la migración 0005. */
export const REALTIME_CITAS_REALES = {
  schema: 'public',
  table: 'citas_cita',
} as const

interface AvisoCita {
  new?: { barber_id?: number }
}

interface Resultado {
  /** `null` mientras carga el primer resultado de esta consulta. */
  franjas: FranjaHoraria[] | null
  error: string | null
}

/**
 * Franjas del barbero para un día, siempre al día.
 *
 * Supabase Realtime avisa cuando cambia una cita (se reprograma, se cancela o
 * alguien reserva) y entonces se vuelven a pedir a la API. El aviso es solo una
 * señal: las franjas siempre salen del backend, que es quien conoce horarios,
 * bloqueos y duración del servicio. Los avisos de otro barbero se ignoran.
 */
export function useFranjas(
  barberoId: number | undefined,
  fecha: string | null,
  duracionMin?: number,
): Resultado {
  const clave =
    barberoId !== undefined && fecha ? `${barberoId}|${fecha}|${duracionMin}` : null
  const [cargado, setCargado] = useState<(Resultado & { clave: string }) | null>(null)

  useEffect(() => {
    if (clave === null || barberoId === undefined || !fecha) return
    let activo = true

    const pedir = () => {
      listarFranjas(barberoId, fecha, duracionMin)
        .then((franjas) => {
          if (activo) setCargado({ clave, franjas, error: null })
        })
        .catch((e: unknown) => {
          if (!activo) return
          const error =
            e instanceof ReservaError
              ? e.message
              : 'No se pudieron cargar los horarios.'
          setCargado({ clave, franjas: [], error })
        })
    }

    pedir()
    // Sin Supabase configurado no hay avisos: solo se consulta al cambiar de día.
    if (!supabase) {
      return () => {
        activo = false
      }
    }
    const cliente = supabase
    const canal = cliente
      .channel(`franjas-${clave}`)
      .on(
        'postgres_changes',
        { event: '*', ...REALTIME_CITAS_REALES },
        (payload: AvisoCita) => {
          // Un DELETE no trae columnas: no se sabe de quién era, se vuelve a pedir.
          const otro = payload.new?.barber_id
          if (otro === undefined || otro === barberoId) pedir()
        },
      )
      .subscribe()

    return () => {
      activo = false
      void cliente.removeChannel(canal)
    }
  }, [clave, barberoId, fecha, duracionMin])

  // Una respuesta de otro día o barbero no se muestra mientras llega la nueva.
  return cargado && cargado.clave === clave
    ? { franjas: cargado.franjas, error: cargado.error }
    : { franjas: null, error: null }
}
