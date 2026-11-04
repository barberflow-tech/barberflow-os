import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('@/lib/catalogoApi', () => ({ listarServiciosApi: vi.fn() }))

import { listarServiciosApi } from '@/lib/catalogoApi'
import { useServicesStore } from './useServicesStore'

describe('useServicesStore.fetchServices', () => {
  beforeEach(() => {
    useServicesStore.setState({ services: [], isLoading: false, error: null })
    vi.mocked(listarServiciosApi).mockReset()
  })

  it('Dado el catálogo del backend, Cuando se carga, Entonces llena el store con valores por defecto', async () => {
    vi.mocked(listarServiciosApi).mockResolvedValue([
      {
        id: 7,
        name: 'Corte',
        price: 35000,
        duration_minutes: 30,
        description: '',
        is_active: true,
      },
    ])
    await useServicesStore.getState().fetchServices()
    const { services, error } = useServicesStore.getState()
    expect(error).toBeNull()
    expect(services).toEqual([
      expect.objectContaining({ id: '7', name: 'Corte', category: 'General' }),
    ])
  })

  it('Dado un fallo del backend, Cuando se carga, Entonces guarda el error', async () => {
    vi.mocked(listarServiciosApi).mockRejectedValue(new Error('sin conexión'))
    await useServicesStore.getState().fetchServices()
    expect(useServicesStore.getState().error).toBe('sin conexión')
  })
})
