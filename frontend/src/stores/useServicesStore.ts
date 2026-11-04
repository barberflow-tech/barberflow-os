import { create } from 'zustand'
import {
  actualizarServicioApi,
  crearServicioApi,
  eliminarServicioApi,
  listarServiciosApi,
  type ServicioApi,
  type ServicioEntrada,
} from '@/lib/catalogoApi'

export interface Service {
  id: string
  name: string
  description: string
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

const aEntrada = (s: Omit<Service, 'id'>): ServicioEntrada => ({
  name: s.name,
  price: s.price,
  duration_minutes: s.duration_minutes,
  description: s.description,
  is_active: s.is_active,
})

// Categoría, destacado e imagen aún no existen en el backend: solo viven en pantalla.
const conExtras = (
  api: ServicioApi,
  extras: Pick<Service, 'category' | 'is_featured' | 'image_url'>,
): Service => ({
  id: String(api.id),
  name: api.name,
  description: api.description,
  duration_minutes: api.duration_minutes,
  price: api.price,
  is_active: api.is_active,
  category: extras.category,
  is_featured: extras.is_featured,
  image_url: extras.image_url,
})

export const useServicesStore = create<ServicesState>((set) => ({
  services: [],

  isLoading: false,
  error: null,

  // Lee el catálogo real. Categoría, destacado e imagen aún no existen en el backend:
  // se conservan los que el panel haya puesto localmente y, si no, valores por defecto.
  fetchServices: async () => {
    set({ isLoading: true, error: null })
    try {
      const desdeApi = await listarServiciosApi({ incluirInactivos: true })
      set((state) => ({
        isLoading: false,
        services: desdeApi.map((s) => {
          const previo = state.services.find((p) => p.id === String(s.id))
          return {
            id: String(s.id),
            name: s.name,
            description: s.description,
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

  // Crear, editar y eliminar van primero al backend y, si responde bien, se refleja
  // en pantalla. Si falla, la acción lanza el error y el estado queda intacto.
  addService: async (datos) => {
    const creado = await crearServicioApi(aEntrada(datos))
    set((state) => ({ services: [...state.services, conExtras(creado, datos)] }))
  },

  updateServiceOptimistic: async (id, cambios) => {
    const actual = useServicesStore.getState().services.find((s) => s.id === id)
    if (!actual) return
    const nuevo = { ...actual, ...cambios }
    const guardado = await actualizarServicioApi(id, aEntrada(nuevo))
    set((state) => ({
      services: state.services.map((s) =>
        s.id === id ? conExtras(guardado, nuevo) : s,
      ),
    }))
  },

  deleteService: async (id) => {
    await eliminarServicioApi(id)
    // El backend desactiva el servicio (borrado lógico): se quita de la lista.
    set((state) => ({ services: state.services.filter((s) => s.id !== id) }))
  },
}))
