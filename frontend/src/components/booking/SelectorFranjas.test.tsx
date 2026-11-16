import { act, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { SelectorFranjas } from './SelectorFranjas'

const canal = vi.hoisted(() => ({ on: vi.fn(), subscribe: vi.fn() }))
const supabaseMock = vi.hoisted(() => ({ channel: vi.fn(), removeChannel: vi.fn() }))
vi.mock('@/lib/supabase', () => ({ supabase: supabaseMock }))
vi.mock('@/lib/reservaApi', async (importOriginal) => {
  const real = await importOriginal<typeof import('@/lib/reservaApi')>()
  return { ReservaError: real.ReservaError, listarFranjas: vi.fn() }
})

import { listarFranjas } from '@/lib/reservaApi'

const props = { barberoId: 9, fecha: '2026-11-20', duracionMin: 45, hora: null }

describe('SelectorFranjas: selector compartido por el asistente y Mis citas', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    canal.on.mockReturnValue(canal)
    canal.subscribe.mockReturnValue(canal)
    supabaseMock.channel.mockReturnValue(canal)
    vi.mocked(listarFranjas).mockResolvedValue([
      { hora: '09:00', disponible: false },
      { hora: '10:00', disponible: true },
    ])
  })

  it('Dado franjas con una ocupada, Cuando se muestran, Entonces la ocupada no se puede elegir', async () => {
    render(<SelectorFranjas {...props} onElegir={vi.fn()} />)

    expect(await screen.findByRole('button', { name: /hora 09:00/i })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Hora 10:00' })).toBeEnabled()
  })

  it('Dado ocultarOcupadas, Cuando se muestran, Entonces solo aparecen las libres', async () => {
    render(<SelectorFranjas {...props} ocultarOcupadas onElegir={vi.fn()} />)

    expect(
      await screen.findByRole('button', { name: 'Hora 10:00' }),
    ).toBeInTheDocument()
    expect(
      screen.queryByRole('button', { name: /hora 09:00/i }),
    ).not.toBeInTheDocument()
  })

  it('Dado una franja libre, Cuando se pulsa, Entonces avisa la hora elegida', async () => {
    const onElegir = vi.fn()
    render(<SelectorFranjas {...props} onElegir={onElegir} />)

    await userEvent
      .setup()
      .click(await screen.findByRole('button', { name: 'Hora 10:00' }))

    expect(onElegir).toHaveBeenCalledWith('10:00')
  })

  it('Dado un día sin franjas libres, Cuando se consulta, Entonces se le avisa', async () => {
    vi.mocked(listarFranjas).mockResolvedValue([])
    render(<SelectorFranjas {...props} onElegir={vi.fn()} />)

    expect(await screen.findByText(/No hay horarios disponibles/)).toBeInTheDocument()
  })

  it('Dado un error del servidor, Cuando falla, Entonces muestra una alerta', async () => {
    vi.mocked(listarFranjas).mockRejectedValue(new Error('boom'))
    render(<SelectorFranjas {...props} onElegir={vi.fn()} />)

    expect(await screen.findByRole('alert')).toHaveTextContent(/No se pudieron cargar/)
  })

  it('Dado una cita reprogramada, Cuando Realtime avisa, Entonces la franja anterior aparece libre sin recargar', async () => {
    vi.mocked(listarFranjas)
      .mockResolvedValueOnce([{ hora: '09:00', disponible: false }])
      .mockResolvedValueOnce([{ hora: '09:00', disponible: true }])
    render(<SelectorFranjas {...props} onElegir={vi.fn()} />)
    expect(
      await screen.findByRole('button', { name: /hora 09:00 \(ocupada\)/i }),
    ).toBeDisabled()

    const manejador = canal.on.mock.calls[0][2] as (p: unknown) => void
    act(() => manejador({ eventType: 'UPDATE', new: { id: 1, barber_id: 9 } }))

    await waitFor(() =>
      expect(screen.getByRole('button', { name: 'Hora 09:00' })).toBeEnabled(),
    )
  })
})
