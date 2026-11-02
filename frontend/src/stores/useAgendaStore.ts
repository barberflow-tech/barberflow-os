import { create } from 'zustand'

/**
 * Borrador: ajustar los campos cuando HU-02 defina el modelo de la reserva.
 * Solo se exige el `id`, que es lo que usa la agenda para no duplicar citas.
 */
export interface Cita {
  id: number | string
  [campo: string]: unknown
}

interface AgendaState {
  citas: Cita[]
  addCita: (cita: Cita) => void
}

export const useAgendaStore = create<AgendaState>()((set) => ({
  citas: [],

  addCita: (cita) =>
    set((state) =>
      state.citas.some((existente) => existente.id === cita.id)
        ? state
        : { citas: [...state.citas, cita] },
    ),
}))
