import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useReservaWizardStore } from '@/stores/useReservaWizardStore'
import { ReservaWizard } from './ReservaWizard'

vi.mock('@/lib/reservaApi', async (importOriginal) => {
  const real = await importOriginal<typeof import('@/lib/reservaApi')>()
  const servicio = {
    id: 1,
    nombre: 'Corte clásico',
    precio: 25000,
    duracionMin: 45,
  }
  const barbero = { id: 1, nombre: 'Thiago', rol: 'Master barber', calificacion: 4.9 }
  return {
    ReservaError: real.ReservaError,
    listarServicios: vi.fn().mockResolvedValue([servicio]),
    listarBarberos: vi.fn().mockResolvedValue([barbero]),
    listarFranjas: vi.fn().mockResolvedValue([
      { hora: '09:00', disponible: true },
      { hora: '10:00', disponible: false },
      { hora: '11:30', disponible: true },
    ]),
    crearCita: vi.fn().mockResolvedValue({
      id: 10,
      estado: 'PENDING',
      servicio,
      barbero,
      inicio: '2026-11-04T11:30:00-05:00',
      total: 25000,
    }),
  }
})

import { crearCita } from '@/lib/reservaApi'

function renderWizard() {
  return render(
    <MemoryRouter>
      <ReservaWizard />
    </MemoryRouter>,
  )
}

async function llegarAlPaso4(user: ReturnType<typeof userEvent.setup>) {
  await user.click(await screen.findByRole('button', { name: /corte clásico/i }))
  await user.click(screen.getByRole('button', { name: /continuar/i }))
  await user.click(await screen.findByRole('button', { name: /thiago/i }))
  await user.click(screen.getByRole('button', { name: /continuar/i }))
  await user.click(await screen.findByRole('button', { name: /hora 11:30/i }))
  await user.click(screen.getByRole('button', { name: /continuar/i }))
}

describe('ReservaWizard', () => {
  beforeEach(() => {
    useReservaWizardStore.getState().reiniciar()
    vi.clearAllMocks()
  })

  it('muestra el paso 1 con los servicios y el avance en 1 de 4', async () => {
    renderWizard()

    expect(await screen.findByText(/corte clásico/i)).toBeInTheDocument()
    expect(screen.getByText(/paso 1 de 4/i)).toBeInTheDocument()
  })

  it('no deja continuar sin elegir un servicio', async () => {
    renderWizard()
    await screen.findByText(/corte clásico/i)

    expect(screen.getByRole('button', { name: /continuar/i })).toBeDisabled()
  })

  it('no permite elegir una franja ocupada', async () => {
    const user = userEvent.setup()
    renderWizard()
    await user.click(await screen.findByRole('button', { name: /corte clásico/i }))
    await user.click(screen.getByRole('button', { name: /continuar/i }))
    await user.click(await screen.findByRole('button', { name: /thiago/i }))
    await user.click(screen.getByRole('button', { name: /continuar/i }))

    expect(await screen.findByRole('button', { name: /hora 10:00/i })).toBeDisabled()
  })

  it('valida el nombre y el celular antes de confirmar', async () => {
    const user = userEvent.setup()
    renderWizard()
    await llegarAlPaso4(user)

    await user.click(screen.getByRole('button', { name: /confirmar reserva/i }))

    expect(
      await screen.findByText(/nombre completo/i, { selector: 'p' }),
    ).toBeInTheDocument()
    expect(crearCita).not.toHaveBeenCalled()
  })

  it('Dado el paso 4, Cuando confirma la reserva, Entonces muestra la pantalla de éxito con el resumen y deja el wizard limpio', async () => {
    const user = userEvent.setup()
    renderWizard()
    await llegarAlPaso4(user)

    await user.type(screen.getByLabelText(/nombre completo/i), 'Juan Esteban Gómez')
    await user.type(screen.getByLabelText(/celular/i), '3004567890')
    await user.click(screen.getByRole('button', { name: /confirmar reserva/i }))

    expect(
      await screen.findByRole('heading', { name: /reserva confirmada/i }),
    ).toBeInTheDocument()
    expect(screen.getByText(/corte clásico/i)).toBeInTheDocument()
    expect(screen.getByText(/thiago/i)).toBeInTheDocument()
    expect(crearCita).toHaveBeenCalledWith({
      servicioId: 1,
      barberoId: 1,
      inicio: expect.stringMatching(/^\d{4}-\d{2}-\d{2}T11:30/),
      contactoNombre: 'Juan Esteban Gómez',
      contactoCelular: '3004567890',
    })

    await waitFor(() => {
      const s = useReservaWizardStore.getState()
      expect(s.servicio).toBeNull()
      expect(s.barbero).toBeNull()
      expect(s.hora).toBeNull()
      expect(s.cita).not.toBeNull()
    })
  })

  it('"Reservar otra cita" reinicia el flujo en el paso 1', async () => {
    const user = userEvent.setup()
    renderWizard()
    await llegarAlPaso4(user)
    await user.type(screen.getByLabelText(/nombre completo/i), 'Juan Esteban Gómez')
    await user.type(screen.getByLabelText(/celular/i), '3004567890')
    await user.click(screen.getByRole('button', { name: /confirmar reserva/i }))
    await screen.findByRole('heading', { name: /reserva confirmada/i })

    await user.click(screen.getByRole('button', { name: /reservar otra cita/i }))

    expect(await screen.findByText(/paso 1 de 4/i)).toBeInTheDocument()
    expect(useReservaWizardStore.getState().cita).toBeNull()
  })

  it('muestra el error si la API no puede registrar la cita', async () => {
    vi.mocked(crearCita).mockRejectedValueOnce(
      new Error('La franja seleccionada ya no esta disponible.'),
    )
    const user = userEvent.setup()
    renderWizard()
    await llegarAlPaso4(user)
    await user.type(screen.getByLabelText(/nombre completo/i), 'Juan Esteban Gómez')
    await user.type(screen.getByLabelText(/celular/i), '3004567890')

    await user.click(screen.getByRole('button', { name: /confirmar reserva/i }))

    expect(await screen.findByRole('alert')).toHaveTextContent(/ya no esta disponible/i)
    expect(
      screen.queryByRole('heading', { name: /reserva confirmada/i }),
    ).not.toBeInTheDocument()
  })
})
