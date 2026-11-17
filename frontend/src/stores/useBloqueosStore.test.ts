import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useBloqueosStore } from './useBloqueosStore'

vi.mock('@/lib/reservaApi', () => ({
  obtenerBloqueosApi: vi.fn(),
  crearBloqueoApi: vi.fn(),
  actualizarBloqueoApi: vi.fn(),
  eliminarBloqueoApi: vi.fn().mockResolvedValue(undefined),
}))

import { actualizarBloqueoApi } from '@/lib/reservaApi'

const bloqueo = (id: number, motivo = 'Incapacidad') => ({
  id,
  barberoId: 3,
  fecha: '2026-12-01',
  horaInicio: '08:00',
  horaFin: '13:00',
  motivo,
})

describe('useBloqueosStore con ids numéricos del backend', () => {
  beforeEach(() => {
    useBloqueosStore.setState({
      bloqueos: [bloqueo(7), bloqueo(8)],
      isLoading: false,
      error: null,
    })
  })

  it('Dado un bloqueo con id numérico, Cuando la pantalla lo elimina con el id como texto, Entonces desaparece de la lista', async () => {
    await useBloqueosStore.getState().eliminarBloqueo('7')

    expect(useBloqueosStore.getState().bloqueos.map((b) => b.id)).toEqual([8])
  })

  it('Dado un bloqueo con id numérico, Cuando la pantalla lo edita con el id como texto, Entonces se reemplaza en la lista', async () => {
    vi.mocked(actualizarBloqueoApi).mockResolvedValue(bloqueo(7, 'Cita médica'))

    await useBloqueosStore.getState().actualizarBloqueo('7', bloqueo(7, 'Cita médica'))

    const lista = useBloqueosStore.getState().bloqueos
    expect(lista).toHaveLength(2)
    expect(lista.find((b) => b.id === 7)?.motivo).toBe('Cita médica')
  })
})
