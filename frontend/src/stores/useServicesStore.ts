import { create } from 'zustand'

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
  version: string
  services: Service[]
  isLoading: boolean
  error: string | null
  fetchServices: () => Promise<void>
  addService: (service: Omit<Service, 'id'>) => Promise<void>
  updateServiceOptimistic: (id: string, updatedData: Partial<Service>) => Promise<void>
  deleteService: (id: string) => Promise<void>
}

export const useServicesStore = create<ServicesState>((set) => ({
  version: 'v4-barber-images',

  services: [
    {
      id: '1',
      name: 'Corte Clásico',
      duration_minutes: 30,
      price: 25000,
      category: 'Cortes',
      is_active: true,
      is_featured: true,
      image_url:
        'https://images.unsplash.com/photo-1599351431202-1e0f0137899a?w=600&auto=format&fit=crop&q=80',
    },
    {
      id: '2',
      name: 'Corte + Barba Premium',
      duration_minutes: 45,
      price: 45000,
      category: 'Combos',
      is_active: true,
      is_featured: true,
      image_url:
        'https://images.unsplash.com/photo-1621605815971-fbc98d665033?w=600&auto=format&fit=crop&q=80',
    },
    {
      id: '3',
      name: 'Perfilado y Afeitado de Barba',
      duration_minutes: 25,
      price: 20000,
      category: 'Barbas',
      is_active: true,
      is_featured: false,
      image_url:
        'https://images.pexels.com/photos/18298039/pexels-photo-18298039.jpeg?auto=compress&cs=tinysrgb&w=600',
    },
    {
      id: '4',
      name: 'Low Fade Texturizado',
      duration_minutes: 40,
      price: 30000,
      category: 'Cortes',
      is_active: true,
      is_featured: true,
      image_url:
        'https://images.unsplash.com/photo-1503951914875-452162b0f3f1?w=600&auto=format&fit=crop&q=80',
    },
    {
      id: '5',
      name: 'Mascarilla Negra & Exfoliación',
      duration_minutes: 20,
      price: 18000,
      category: 'Tratamientos',
      is_active: true,
      is_featured: false,
      image_url:
        'https://umbraco.departures-international.com/media/uhkesuwq/angan-credit-ari-magg.jpg?anchor=center&format=auto&mode=min&width=1440',
    },
    {
      id: '6',
      name: 'Corte Skin Fade + Diseño',
      duration_minutes: 50,
      price: 38000,
      category: 'Cortes',
      is_active: true,
      is_featured: false,
      image_url:
        'https://images.unsplash.com/photo-1622286342621-4bd786c2447c?w=600&auto=format&fit=crop&q=80',
    },
  ],

  isLoading: false,
  error: null,

  fetchServices: async () => {},

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
