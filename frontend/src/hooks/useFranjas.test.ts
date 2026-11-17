import { act, renderHook, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useFranjas } from './useFranjas'

const canal = vi.hoisted(() => ({ on: vi.fn(), subscribe: vi.fn() }))
const supabaseMock = vi.hoisted(() => ({ channel: vi.fn(), removeChannel: vi.fn() }))
vi.mock('@/lib/supabase', () => ({ supabase: supabaseMock }))
vi.mock('@/lib/reservaApi', async (importOriginal) => {
  const real = await importOriginal<typeof import('@/lib/reservaApi')>()
  return { ReservaError: real.ReservaError, listarFranjas: vi.fn() }
})

import { listarFranjas } from '@/lib/reservaApi'

/** Simula el aviso de Supabase Realtime sobre la tabla de citas. */
function emitir(payload: { eventType: string; new?: Record<string, unknown> }) {
  const manejador = canal.on.mock.calls[0][2] as (p: unknown) => void
  act(() => manejador(payload))
}

describe('useFranjas (SCRUM-54)', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    canal.on.mockReturnValue(canal)
    canal.subscribe.mockReturnValue(canal)
    supabaseMock.channel.mockReturnValue(canal)
    vi.mocked(listarFranjas).mockResolvedValue([{ hora: '09:00', disponible: true }])
  })

  it('Dado un barbero y un día, Cuando se monta, Entonces pide las franjas de ese día', async () => {
    const { result } = renderHook(() => useFranjas(9, '2026-11-20', 45))

    expect(result.current.franjas).toBeNull()
    await waitFor(() =>
      expect(result.current.franjas).toEqual([{ hora: '09:00', disponible: true }]),
    )
    expect(listarFranjas).toHaveBeenCalledWith(9, '2026-11-20', 45)
  })

  it('Dado que se reprogramó una cita, Cuando Realtime avisa un cambio, Entonces la franja liberada aparece sin recargar la página', async () => {
    vi.mocked(listarFranjas)
      .mockResolvedValueOnce([{ hora: '09:00', disponible: false }])
      .mockResolvedValueOnce([{ hora: '09:00', disponible: true }])
    const { result } = renderHook(() => useFranjas(9, '2026-11-20', 45))
    await waitFor(() => expect(result.current.franjas?.[0].disponible).toBe(false))

    emitir({ eventType: 'UPDATE', new: { id: 1, barber_id: 9, status: 'PENDING' } })

    await waitFor(() => expect(result.current.franjas?.[0].disponible).toBe(true))
    expect(listarFranjas).toHaveBeenCalledTimes(2)
  })

  it('Dado un cambio de otro barbero, Cuando llega el aviso, Entonces no vuelve a pedir las franjas', async () => {
    const { result } = renderHook(() => useFranjas(9, '2026-11-20', 45))
    await waitFor(() => expect(result.current.franjas).not.toBeNull())

    emitir({ eventType: 'UPDATE', new: { id: 1, barber_id: 77 } })

    expect(listarFranjas).toHaveBeenCalledTimes(1)
  })

  it('Dado un DELETE (sin columnas en el aviso), Cuando llega, Entonces vuelve a pedir las franjas por si era de este barbero', async () => {
    const { result } = renderHook(() => useFranjas(9, '2026-11-20', 45))
    await waitFor(() => expect(result.current.franjas).not.toBeNull())

    emitir({ eventType: 'DELETE' })

    await waitFor(() => expect(listarFranjas).toHaveBeenCalledTimes(2))
  })

  it('Dado que el cliente cambia de día, Cuando cambian los datos, Entonces pide el nuevo día y descarta la respuesta anterior', async () => {
    let resolverViejo: (f: { hora: string; disponible: boolean }[]) => void = () => {}
    vi.mocked(listarFranjas)
      .mockReturnValueOnce(new Promise((r) => (resolverViejo = r)))
      .mockResolvedValueOnce([{ hora: '15:00', disponible: true }])
    const { result, rerender } = renderHook(({ f }) => useFranjas(9, f, 45), {
      initialProps: { f: '2026-11-20' },
    })

    rerender({ f: '2026-11-21' })
    await waitFor(() => expect(result.current.franjas?.[0].hora).toBe('15:00'))
    resolverViejo([{ hora: '09:00', disponible: true }])

    await act(async () => {})
    expect(result.current.franjas?.[0].hora).toBe('15:00')
  })

  it('Dado un error del servidor, Cuando falla, Entonces expone el mensaje y no deja franjas', async () => {
    vi.mocked(listarFranjas).mockRejectedValue(new Error('boom'))
    const { result } = renderHook(() => useFranjas(9, '2026-11-20', 45))

    await waitFor(() =>
      expect(result.current.error).toBe('No se pudieron cargar los horarios.'),
    )
    expect(result.current.franjas).toEqual([])
  })

  it('Dado que no hay barbero o fecha, Cuando se monta, Entonces no consulta ni se suscribe', () => {
    renderHook(() => useFranjas(undefined, null, 45))

    expect(listarFranjas).not.toHaveBeenCalled()
    expect(supabaseMock.channel).not.toHaveBeenCalled()
  })

  it('Dado un selector abierto, Cuando se desmonta, Entonces libera el canal de Realtime', async () => {
    const { unmount, result } = renderHook(() => useFranjas(9, '2026-11-20', 45))
    await waitFor(() => expect(result.current.franjas).not.toBeNull())

    unmount()

    expect(supabaseMock.removeChannel).toHaveBeenCalledWith(canal)
  })

  it('Dado la tabla real de citas, Cuando se suscribe, Entonces escucha todos los eventos de public.citas_cita', async () => {
    const { result } = renderHook(() => useFranjas(9, '2026-11-20', 45))
    await waitFor(() => expect(result.current.franjas).not.toBeNull())

    expect(canal.on).toHaveBeenCalledWith(
      'postgres_changes',
      { event: '*', schema: 'public', table: 'citas_cita' },
      expect.any(Function),
    )
  })
})
