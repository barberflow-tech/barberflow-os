import { create } from 'zustand'
import {
  listarMisCitasApi,
  listarCitasCanceladasApi,
  cancelarCitaApi,
  reprogramarCitaApi,
  type CitaConfirmada,
  type CitaHistorial,
} from '@/lib/reservaApi'

interface CitasState {
  citas: CitaConfirmada[]
  isLoading: boolean
  error: string | null
  canceladas: CitaHistorial[]
  cargandoCanceladas: boolean
  errorCanceladas: string | null
  fetchMisCitas: () => Promise<void>
  fetchCanceladas: () => Promise<void>
  /** Devuelve si la cancelación quedó registrada como tardía (la antelación mínima o menos). */
  cancelarCita: (citaId: number | string) => Promise<{ tardia: boolean }>
  reprogramarCita: (citaId: number | string, nuevoInicio: string) => Promise<void>
}

export const useCitasStore = create<CitasState>((set, get) => ({
  citas: [],
  isLoading: false,
  error: null,
  canceladas: [],
  cargandoCanceladas: false,
  errorCanceladas: null,

  fetchCanceladas: async () => {
    set({ cargandoCanceladas: true, errorCanceladas: null })
    try {
      const canceladas = await listarCitasCanceladasApi()
      set({ canceladas, cargandoCanceladas: false })
    } catch (e) {
      set({
        cargandoCanceladas: false,
        errorCanceladas:
          e instanceof Error
            ? e.message
            : 'No se pudieron cargar tus citas canceladas.',
      })
    }
  },

  fetchMisCitas: async () => {
    set({ isLoading: true, error: null })
    try {
      const citasApi = await listarMisCitasApi()
      set({ citas: citasApi, isLoading: false })
    } catch (e) {
      set({
        isLoading: false,
        error: e instanceof Error ? e.message : 'No se pudieron cargar tus citas.',
      })
    }
  },

  cancelarCita: async (citaId) => {
    const resultado = await cancelarCitaApi(citaId)
    set((state) => ({
      citas: state.citas.filter((c) => c.id !== citaId),
    }))
    return resultado
  },

  reprogramarCita: async (citaId, nuevoInicio) => {
    const actual = get().citas.find((c) => c.id === citaId)
    if (!actual) throw new Error('No encontramos esa cita en tu lista.')
    const citaActualizada = await reprogramarCitaApi(actual, nuevoInicio)
    set((state) => ({
      citas: state.citas.map((c) => (c.id === citaId ? citaActualizada : c)),
    }))
  },
}))
