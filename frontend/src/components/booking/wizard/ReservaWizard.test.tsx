import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { useAuthStore } from '@/stores/useAuthStore'
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

  it('Dado que elige fecha y hora, Cuando pulsa Continuar, Entonces pasa al paso 4 sin agendar y avisa que falta confirmar', async () => {
    const user = userEvent.setup()
    renderWizard()
    await llegarAlPaso4(user)

    expect(screen.getByText(/paso 4 de 4/i)).toBeInTheDocument()
    expect(crearCita).not.toHaveBeenCalled()
    expect(useReservaWizardStore.getState().cita).toBeNull()
    expect(screen.getByText(/tu cita aún no está agendada/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /confirmar reserva/i })).toBeEnabled()
  })

  it('Dado el paso 3, Cuando hace doble clic en Continuar, Entonces no agenda: Confirmar no ocupa el lugar de Continuar', async () => {
    const user = userEvent.setup()
    renderWizard()
    await user.click(await screen.findByRole('button', { name: /corte clásico/i }))
    await user.click(screen.getByRole('button', { name: /continuar/i }))
    await user.click(await screen.findByRole('button', { name: /thiago/i }))
    await user.click(screen.getByRole('button', { name: /continuar/i }))
    await user.click(await screen.findByRole('button', { name: /hora 11:30/i }))

    await user.dblClick(screen.getByRole('button', { name: /continuar/i }))

    expect(screen.getByText(/paso 4 de 4/i)).toBeInTheDocument()
    expect(crearCita).not.toHaveBeenCalled()
    // El botón de confirmar vive dentro del formulario del paso 4, no en el pie.
    const confirmar = screen.getByRole('button', { name: /confirmar reserva/i })
    expect(confirmar.closest('form')).toHaveAttribute('id', 'form-confirmar')
    expect(confirmar.closest('footer')).toBeNull()
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
      barbero: expect.objectContaining({ id: 1, nombre: 'Thiago' }),
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

describe('ReservaWizard: datos de contacto según la sesión', () => {
  beforeEach(() => {
    useReservaWizardStore.getState().reiniciar()
    vi.clearAllMocks()
  })
  afterEach(() => {
    useAuthStore.setState({ accessToken: null, user: null })
  })

  it('Dado un visitante sin cuenta, Cuando llega a confirmar, Entonces se le piden nombre y celular', async () => {
    const user = userEvent.setup()
    renderWizard()
    await llegarAlPaso4(user)

    expect(screen.getByLabelText(/nombre completo/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/celular/i)).toBeInTheDocument()
  })

  it('Dado un cliente con sesión, Cuando llega a confirmar, Entonces su nombre ya está escrito y el celular vacío', async () => {
    useAuthStore.setState({
      accessToken: 'tok',
      user: {
        id: 5,
        email: 'cliente@barberflow.test',
        role: 'cliente',
        fullName: 'Ana Pérez',
      },
    })
    const user = userEvent.setup()
    renderWizard()
    await llegarAlPaso4(user)

    expect(screen.getByLabelText(/nombre completo/i)).toHaveValue('Ana Pérez')
    expect(screen.getByLabelText(/celular/i)).toHaveValue('')
  })

  it('Dado un admin que agenda para un cliente, Cuando llega a confirmar, Entonces el nombre queda vacío para escribir el del cliente', async () => {
    useAuthStore.setState({
      accessToken: 'tok',
      user: {
        id: 2,
        email: 'admin@barberflow.test',
        role: 'admin',
        fullName: 'Ana Admin',
      },
    })
    const user = userEvent.setup()
    renderWizard()
    await llegarAlPaso4(user)

    expect(screen.getByLabelText(/nombre completo/i)).toHaveValue('')
    expect(screen.getByLabelText(/celular/i)).toHaveValue('')
  })

  it('Dado un cliente con sesión, Cuando no escribe su celular, Entonces no se agenda y se le pide', async () => {
    useAuthStore.setState({
      accessToken: 'tok',
      user: {
        id: 5,
        email: 'cliente@barberflow.test',
        role: 'cliente',
        fullName: 'Ana Pérez',
      },
    })
    const user = userEvent.setup()
    renderWizard()
    await llegarAlPaso4(user)

    await user.click(screen.getByRole('button', { name: /confirmar reserva/i }))

    expect(await screen.findByText(/celular/i, { selector: 'p' })).toBeInTheDocument()
    expect(crearCita).not.toHaveBeenCalled()
  })

  it('Dado un cliente con sesión, Cuando pulsa Continuar en el paso 3, Entonces no se agenda hasta que confirme', async () => {
    useAuthStore.setState({
      accessToken: 'tok',
      user: { id: 5, email: 'cliente@barberflow.test', role: 'cliente' },
    })
    const user = userEvent.setup()
    renderWizard()
    await llegarAlPaso4(user)

    expect(crearCita).not.toHaveBeenCalled()
    expect(useReservaWizardStore.getState().cita).toBeNull()
    expect(screen.getByText(/paso 4 de 4/i)).toBeInTheDocument()
  })

  it('Dado un cliente con sesión, Cuando completa su celular y confirma, Entonces reserva con su nombre y ese celular', async () => {
    useAuthStore.setState({
      accessToken: 'tok',
      user: {
        id: 5,
        email: 'cliente@barberflow.test',
        role: 'cliente',
        fullName: 'Ana Pérez',
      },
    })
    const user = userEvent.setup()
    renderWizard()
    await llegarAlPaso4(user)

    await user.type(screen.getByLabelText(/celular/i), '3004567890')
    await user.click(screen.getByRole('button', { name: /confirmar reserva/i }))

    expect(
      await screen.findByRole('heading', { name: /reserva confirmada/i }),
    ).toBeInTheDocument()
    expect(crearCita).toHaveBeenCalledTimes(1)
    expect(vi.mocked(crearCita).mock.calls[0][0]).toMatchObject({
      contactoNombre: 'Ana Pérez',
      contactoCelular: '3004567890',
    })
  })
})
