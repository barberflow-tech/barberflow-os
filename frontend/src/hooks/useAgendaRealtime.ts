import { useEffect } from 'react'
import { supabase } from '@/lib/supabase'
import { type Cita, useAgendaStore } from '@/stores/useAgendaStore'

/** Borrador: ajustar tabla y esquema cuando HU-02 cree la tabla real de reservas. */
export const REALTIME_CITAS = { schema: 'public', table: 'citas' } as const

/** Mantiene la agenda al día: agrega cada cita nueva que Supabase Realtime avise. */
export function useAgendaRealtime() {
  const addCita = useAgendaStore((state) => state.addCita)

  useEffect(() => {
    const canal = supabase
      .channel('agenda-citas')
      .on(
        'postgres_changes',
        { event: 'INSERT', schema: REALTIME_CITAS.schema, table: REALTIME_CITAS.table },
        (payload) => addCita(payload.new as Cita),
      )
      .subscribe()

    return () => {
      void supabase.removeChannel(canal)
    }
  }, [addCita])
}
