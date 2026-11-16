import { render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { Barbero } from '@/lib/reservaApi'
import { useReservaWizardStore } from '@/stores/useReservaWizardStore'
import { PasoFechaHora } from './PasoFechaHora'

vi.mock('@/lib/reservaApi', async (importOriginal) => {
  const real = await importOriginal<typeof import('@/lib/reservaApi')>()
  return {
    ReservaError: real.ReservaError,
    listarFranjas: vi.fn().mockResolvedValue([{ hora: '09:00', disponible: true }]),
  }
})

import { listarFranjas } from '@/lib/reservaApi'

const barbero = (diasLaborales?: number[]): Barbero => ({
  id: 1,
  nombre: 'Thiago',
  rol: 'Master barber',
  calificacion: 4.9,
  diasLaborales,
})

const LUNES_A_SABADO = [0, 1, 2, 3, 4, 5]

/** Fija "hoy" sin congelar los temporizadores que usan los componentes. */
function hoyEs(iso: string) {
  vi.useFakeTimers({ toFake: ['Date'] })
  vi.setSystemTime(new Date(`${iso}T12:00:00-05:00`))
}

function prepararBarbero(b: Barbero) {
  useReservaWizardStore.getState().reiniciar()
  useReservaWizardStore.getState().seleccionarBarbero(b)
}

describe('PasoFechaHora: días según el horario del barbero', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })
  afterEach(() => {
    vi.useRealTimers()
  })

  it('Dado un barbero que no atiende los domingos, Cuando se ve el calendario, Entonces el domingo no se puede elegir', () => {
    hoyEs('2026-11-18') // miércoles
    prepararBarbero(barbero(LUNES_A_SABADO))
    render(<PasoFechaHora />)

    expect(
      screen.getByRole('button', { name: /domingo, 22 de noviembre/i }),
    ).toBeDisabled()
    expect(
      screen.getByRole('button', { name: /sábado, 21 de noviembre/i }),
    ).toBeEnabled()
    expect(
      screen.getByRole('button', { name: /lunes, 23 de noviembre/i }),
    ).toBeEnabled()
    expect(screen.getByText(/días tachados Thiago no atiende/i)).toBeInTheDocument()
  })

  it('Dado que hoy es el día libre del barbero, Cuando se abre el calendario, Entonces empieza en el siguiente día que sí atiende', async () => {
    hoyEs('2026-11-22') // domingo
    prepararBarbero(barbero(LUNES_A_SABADO))
    render(<PasoFechaHora />)

    await waitFor(() =>
      expect(useReservaWizardStore.getState().fecha).toBe('2026-11-23'),
    )
    await waitFor(() =>
      expect(listarFranjas).toHaveBeenCalledWith(1, '2026-11-23', undefined),
    )
  })

  it('Dado un barbero que atiende todos los días, Cuando se ve el calendario, Entonces no se tacha ningún día', () => {
    hoyEs('2026-11-18')
    prepararBarbero(barbero([0, 1, 2, 3, 4, 5, 6]))
    render(<PasoFechaHora />)

    expect(
      screen.getByRole('button', { name: /domingo, 22 de noviembre/i }),
    ).toBeEnabled()
    expect(screen.queryByText(/días tachados/i)).not.toBeInTheDocument()
  })

  it('Dado que no hay dato del horario, Cuando se ve el calendario, Entonces se comporta como antes', () => {
    hoyEs('2026-11-18')
    prepararBarbero(barbero(undefined))
    render(<PasoFechaHora />)

    expect(
      screen.getByRole('button', { name: /domingo, 22 de noviembre/i }),
    ).toBeEnabled()
  })

  it('Dado un barbero sin horario configurado, Cuando se ve el paso, Entonces se avisa y no se piden franjas', () => {
    hoyEs('2026-11-18')
    prepararBarbero(barbero([]))
    render(<PasoFechaHora />)

    expect(screen.getByRole('status')).toHaveTextContent(
      /aún no tiene un horario configurado/i,
    )
    expect(listarFranjas).not.toHaveBeenCalled()
  })
})
