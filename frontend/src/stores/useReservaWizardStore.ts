import { create } from 'zustand'
import type { Barbero, CitaConfirmada, Servicio } from '@/lib/reservaApi'

export type PasoReserva = 1 | 2 | 3 | 4

interface ReservaWizardState {
  paso: PasoReserva
  servicio: Servicio | null
  barbero: Barbero | null
  fecha: string | null // YYYY-MM-DD
  hora: string | null // HH:mm
  cita: CitaConfirmada | null
  seleccionarServicio: (s: Servicio) => void
  seleccionarBarbero: (b: Barbero) => void
  seleccionarFecha: (f: string) => void
  seleccionarHora: (h: string) => void
  siguiente: () => void
  atras: () => void
  registrarCita: (c: CitaConfirmada) => void
  reiniciar: () => void
}

const inicial = {
  paso: 1 as PasoReserva,
  servicio: null,
  barbero: null,
  fecha: null,
  hora: null,
  cita: null,
}

export const useReservaWizardStore = create<ReservaWizardState>((set, get) => ({
  ...inicial,
  seleccionarServicio: (servicio) => set({ servicio }),
  seleccionarBarbero: (barbero) => {
    if (get().barbero?.id === barbero.id) return
    set({ barbero, fecha: null, hora: null })
  },
  seleccionarFecha: (fecha) => {
    if (get().fecha === fecha) return
    set({ fecha, hora: null })
  },
  seleccionarHora: (hora) => set({ hora }),
  siguiente: () => {
    const { paso, servicio, barbero, fecha, hora } = get()
    const completo =
      (paso === 1 && !!servicio) ||
      (paso === 2 && !!barbero) ||
      (paso === 3 && !!fecha && !!hora)
    if (completo) set({ paso: (paso + 1) as PasoReserva })
  },
  atras: () => {
    const { paso } = get()
    if (paso > 1) set({ paso: (paso - 1) as PasoReserva })
  },
  // Al terminar el flujo se limpia todo y solo queda el resumen de la cita.
  registrarCita: (cita) => set({ ...inicial, cita }),
  reiniciar: () => set({ ...inicial }),
}))
