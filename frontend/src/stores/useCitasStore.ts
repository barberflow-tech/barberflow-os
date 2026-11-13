import { create } from 'zustand'
import {
  listarMisCitasApi,
  cancelarCitaApi,
  reprogramarCitaApi,
  type CitaConfirmada,
} from '@/lib/reservaApi'

interface CitasState {
  citas: CitaConfirmada[]
  isLoading: boolean
  error: string | null
  fetchMisCitas: () => Promise<void>
  cancelarCita: (citaId: number | string) => Promise<void>
  reprogramarCita: (citaId: number | string, nuevoInicio: string) => Promise<void>
}

export const useCitasStore = create<CitasState>((set) => ({
  citas: [],
  isLoading: false,
  error: null,

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
    await cancelarCitaApi(citaId)
    set((state) => ({
      citas: state.citas.filter((c) => c.id !== citaId),
    }))
  },

  reprogramarCita: async (citaId, nuevoInicio) => {
    const citaActualizada = await reprogramarCitaApi(citaId, nuevoInicio)
    set((state) => ({
      citas: state.citas.map((c) => (c.id === citaId ? citaActualizada : c)),
    }))
  },
}))
