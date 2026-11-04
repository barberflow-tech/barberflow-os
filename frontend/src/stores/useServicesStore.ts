import { create } from 'zustand'
import { listarServiciosApi } from '@/lib/catalogoApi'

export interface Service {
  id: string
  name: string
  duration_minutes: number
  price: number
  category: string
  is_active: boolean
  is_featured: boolean
  image_url: string
}

interface ServicesState {
  services: Service[]
  isLoading: boolean
  error: string | null
  fetchServices: () => Promise<void>
  addService: (service: Omit<Service, 'id'>) => Promise<void>
  updateServiceOptimistic: (id: string, updatedData: Partial<Service>) => Promise<void>
  deleteService: (id: string) => Promise<void>
}

export const useServicesStore = create<ServicesState>((set) => ({
  services: [],

  isLoading: false,
  error: null,

  // Lee el catálogo real. Categoría, destacado e imagen aún no existen en el backend:
  // se conservan los que el panel haya puesto localmente y, si no, valores por defecto.
  fetchServices: async () => {
    set({ isLoading: true, error: null })
    try {
      const desdeApi = await listarServiciosApi()
      set((state) => ({
        isLoading: false,
        services: desdeApi.map((s) => {
          const previo = state.services.find((p) => p.id === String(s.id))
          return {
            id: String(s.id),
            name: s.name,
            duration_minutes: s.duration_minutes,
            price: s.price,
            is_active: s.is_active,
            category: previo?.category ?? 'General',
            is_featured: previo?.is_featured ?? false,
            image_url: previo?.image_url ?? '',
          }
        }),
      }))
    } catch (e) {
      set({
        isLoading: false,
        error: e instanceof Error ? e.message : 'No se pudieron cargar los servicios.',
      })
    }
  },

  addService: async (newServiceData) => {
    const newService: Service = {
      ...newServiceData,
      id: Date.now().toString(),
    }

    set((state) => ({
      services: [...state.services, newService],
    }))
  },

  updateServiceOptimistic: async (id, updatedData) => {
    set((state) => ({
      services: state.services.map((service) =>
        service.id === id ? { ...service, ...updatedData } : service,
      ),
    }))
  },

  deleteService: async (id) => {
    set((state) => ({
      services: state.services.filter((service) => service.id !== id),
    }))
  },
}))
