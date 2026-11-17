import { renderHook, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useFranjas } from './useFranjas'

// Sin VITE_SUPABASE_ANON_KEY el cliente es null: la reserva debe seguir funcionando.
vi.mock('@/lib/supabase', () => ({ supabase: null }))
vi.mock('@/lib/reservaApi', async (importOriginal) => {
  const real = await importOriginal<typeof import('@/lib/reservaApi')>()
  return { ReservaError: real.ReservaError, listarFranjas: vi.fn() }
})

import { listarFranjas } from '@/lib/reservaApi'

describe('useFranjas sin Supabase configurado', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(listarFranjas).mockResolvedValue([{ hora: '09:00', disponible: true }])
  })

  it('Dado que no hay llave de Supabase, Cuando se piden franjas, Entonces carga desde la API sin Realtime y sin fallar', async () => {
    const { result, unmount } = renderHook(() => useFranjas(9, '2026-11-20', 45))

    await waitFor(() => expect(result.current.franjas).toHaveLength(1))
    expect(result.current.error).toBeNull()
    expect(() => unmount()).not.toThrow()
  })
})
