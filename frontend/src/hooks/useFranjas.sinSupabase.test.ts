import { renderHook, waitFor } from '@testing-library/react'
import { act } from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
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

  describe('franjas desactualizadas (otra pestaña canceló o reservó)', () => {
    afterEach(() => {
      vi.useRealTimers()
    })

    it('Dado que se liberó una franja en otra pestaña, Cuando el cliente vuelve a esta pestaña, Entonces la franja aparece sin recargar', async () => {
      vi.mocked(listarFranjas).mockResolvedValueOnce([
        { hora: '09:00', disponible: true },
      ])
      const { result } = renderHook(() => useFranjas(1, '2026-11-17', 30))
      await waitFor(() => expect(result.current.franjas).toHaveLength(1))

      vi.mocked(listarFranjas).mockResolvedValue([
        { hora: '09:00', disponible: true },
        { hora: '12:30', disponible: true },
      ])
      act(() => {
        document.dispatchEvent(new Event('visibilitychange'))
      })

      await waitFor(() => expect(result.current.franjas).toHaveLength(2))
    })

    it('Dado que la pestaña recupera el foco, Cuando el usuario regresa a la ventana, Entonces se vuelven a pedir las franjas', async () => {
      const { result } = renderHook(() => useFranjas(1, '2026-11-17', 30))
      await waitFor(() => expect(result.current.franjas).toHaveLength(1))
      const antes = vi.mocked(listarFranjas).mock.calls.length

      act(() => {
        window.dispatchEvent(new Event('focus'))
      })

      await waitFor(() =>
        expect(vi.mocked(listarFranjas).mock.calls.length).toBeGreaterThan(antes),
      )
    })

    it('Dado que la pestaña sigue abierta, Cuando pasan 30 segundos, Entonces se actualizan las franjas solas', async () => {
      vi.useFakeTimers({ shouldAdvanceTime: true })
      const { result } = renderHook(() => useFranjas(1, '2026-11-17', 30))
      await waitFor(() => expect(result.current.franjas).toHaveLength(1))
      const antes = vi.mocked(listarFranjas).mock.calls.length

      await act(async () => {
        await vi.advanceTimersByTimeAsync(30_000)
      })

      expect(vi.mocked(listarFranjas).mock.calls.length).toBeGreaterThan(antes)
    })

    it('Dado que se desmonta, Cuando vuelve el foco, Entonces ya no pide franjas', async () => {
      const { result, unmount } = renderHook(() => useFranjas(1, '2026-11-17', 30))
      await waitFor(() => expect(result.current.franjas).toHaveLength(1))
      unmount()
      const antes = vi.mocked(listarFranjas).mock.calls.length

      window.dispatchEvent(new Event('focus'))

      expect(vi.mocked(listarFranjas).mock.calls.length).toBe(antes)
    })
  })
})
