import { create } from 'zustand'
import {
  obtenerBloqueosApi,
  crearBloqueoApi,
  actualizarBloqueoApi,
  eliminarBloqueoApi,
  type Bloqueo,
} from '@/lib/reservaApi'

interface BloqueosState {
  bloqueos: Bloqueo[]
  isLoading: boolean
  error: string | null

  fetchBloqueos: () => Promise<void>
  crearBloqueo: (bloqueo: Omit<Bloqueo, 'id'>) => Promise<void>
  actualizarBloqueo: (id: string, cambios: Omit<Bloqueo, 'id'>) => Promise<void>
  eliminarBloqueo: (id: string) => Promise<void>
}

export const useBloqueosStore = create<BloqueosState>((set) => ({
  bloqueos: [],
  isLoading: false,
  error: null,

  fetchBloqueos: async () => {
    set({ isLoading: true, error: null })

    try {
      const data = await obtenerBloqueosApi()
      set({ bloqueos: data, isLoading: false })
    } catch (e: unknown) {
      set({
        isLoading: false,
        error: e instanceof Error ? e.message : 'Error al cargar bloqueos',
      })
      throw e
    }
  },

  crearBloqueo: async (bloqueo) => {
    set({ isLoading: true, error: null })

    try {
      const nuevo = await crearBloqueoApi(bloqueo)

      set((state) => ({
        bloqueos: [...state.bloqueos, nuevo],
        isLoading: false,
      }))
    } catch (e: unknown) {
      set({
        isLoading: false,
        error: e instanceof Error ? e.message : 'Error al crear bloqueo',
      })
      throw e
    }
  },

  actualizarBloqueo: async (id, cambios) => {
    set({ isLoading: true, error: null })

    try {
      const actualizado = await actualizarBloqueoApi(id, cambios)

      set((state) => ({
        bloqueos: state.bloqueos.map((b) => (b.id === id ? actualizado : b)),
        isLoading: false,
      }))
    } catch (e: unknown) {
      set({
        isLoading: false,
        error: e instanceof Error ? e.message : 'Error al actualizar bloqueo',
      })
      throw e
    }
  },

  eliminarBloqueo: async (id) => {
    set({ isLoading: true, error: null })

    try {
      await eliminarBloqueoApi(id)

      set((state) => ({
        bloqueos: state.bloqueos.filter((b) => b.id !== id),
        isLoading: false,
      }))
    } catch (e: unknown) {
      set({
        isLoading: false,
        error: e instanceof Error ? e.message : 'Error al eliminar bloqueo',
      })
      throw e
    }
  },
}))
