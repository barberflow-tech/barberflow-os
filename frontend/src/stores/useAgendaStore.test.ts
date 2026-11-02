import { beforeEach, describe, expect, it } from 'vitest'
import { useAgendaStore } from './useAgendaStore'

describe('useAgendaStore', () => {
  beforeEach(() => {
    useAgendaStore.setState(useAgendaStore.getInitialState(), true)
  })

  it('Dado que el panel abre, Cuando aún no llegan citas, Entonces la agenda está vacía', () => {
    expect(useAgendaStore.getState().citas).toEqual([])
  })

  it('Dado una agenda vacía, Cuando llega una cita nueva, Entonces se agrega a la agenda', () => {
    useAgendaStore.getState().addCita({ id: 1, inicio: '2026-11-02T10:00:00Z' })

    expect(useAgendaStore.getState().citas).toEqual([
      { id: 1, inicio: '2026-11-02T10:00:00Z' },
    ])
  })

  it('Dado una cita ya en la agenda, Cuando llega el mismo evento otra vez, Entonces no se duplica', () => {
    const { addCita } = useAgendaStore.getState()

    addCita({ id: 1 })
    addCita({ id: 1 })

    expect(useAgendaStore.getState().citas).toHaveLength(1)
  })
})
