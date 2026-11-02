import { renderHook } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useAgendaStore } from '@/stores/useAgendaStore'
import { REALTIME_CITAS, useAgendaRealtime } from './useAgendaRealtime'

const canal = vi.hoisted(() => ({
  on: vi.fn(),
  subscribe: vi.fn(),
}))
const supabaseMock = vi.hoisted(() => ({
  channel: vi.fn(),
  removeChannel: vi.fn(),
}))

vi.mock('@/lib/supabase', () => ({ supabase: supabaseMock }))

/** Simula el aviso que Supabase Realtime envía cuando se inserta una fila. */
function emitirInsert(nueva: Record<string, unknown>) {
  const manejador = canal.on.mock.calls[0][2] as (payload: { new: unknown }) => void
  manejador({ new: nueva })
}

describe('useAgendaRealtime', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    canal.on.mockReturnValue(canal)
    canal.subscribe.mockReturnValue(canal)
    supabaseMock.channel.mockReturnValue(canal)
    useAgendaStore.setState(useAgendaStore.getInitialState(), true)
  })

  it('Dado el panel del barbero/admin, Cuando se abre, Entonces escucha los INSERT de citas por Realtime', () => {
    renderHook(() => useAgendaRealtime())

    expect(supabaseMock.channel).toHaveBeenCalledTimes(1)
    expect(canal.on).toHaveBeenCalledWith(
      'postgres_changes',
      { event: 'INSERT', schema: REALTIME_CITAS.schema, table: REALTIME_CITAS.table },
      expect.any(Function),
    )
    expect(canal.subscribe).toHaveBeenCalledTimes(1)
  })

  it('Dado un cliente agendando vía web, Cuando la reserva se confirma, Entonces la agenda del panel se actualiza al instante', () => {
    renderHook(() => useAgendaRealtime())

    emitirInsert({ id: 7, inicio: '2026-11-02T10:00:00Z' })

    expect(useAgendaStore.getState().citas).toEqual([
      { id: 7, inicio: '2026-11-02T10:00:00Z' },
    ])
  })

  it('Dado que Realtime reenvía el mismo evento, Cuando llega dos veces, Entonces la cita aparece una sola vez', () => {
    renderHook(() => useAgendaRealtime())

    emitirInsert({ id: 7 })
    emitirInsert({ id: 7 })

    expect(useAgendaStore.getState().citas).toHaveLength(1)
  })

  it('Dado un panel suscrito, Cuando se cierra, Entonces deja de escuchar y libera el canal', () => {
    const { unmount } = renderHook(() => useAgendaRealtime())

    unmount()

    expect(supabaseMock.removeChannel).toHaveBeenCalledWith(canal)
  })
})
