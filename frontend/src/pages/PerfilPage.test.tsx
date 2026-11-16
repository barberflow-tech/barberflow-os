import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { CitaConfirmada } from '@/lib/reservaApi'
import { useAuthStore } from '@/stores/useAuthStore'
import { useCitasStore } from '@/stores/useCitasStore'
import { PerfilPage } from './PerfilPage'

vi.mock('@/lib/reservaApi', async (importOriginal) => {
  const real = await importOriginal<typeof import('@/lib/reservaApi')>()
  return {
    ReservaError: real.ReservaError,
    listarMisCitasApi: vi.fn(),
    cancelarCitaApi: vi.fn(),
    reprogramarCitaApi: vi.fn(),
    listarFranjas: vi.fn(),
  }
})

import {
  cancelarCitaApi,
  listarFranjas,
  listarMisCitasApi,
  reprogramarCitaApi,
} from '@/lib/reservaApi'

const HORA = 60 * 60 * 1000
const ANTELACION = 2

/** Instante en hora de Colombia, con el formato que entrega el cliente de la API. */
const enColombia = (ms: number) =>
  new Date(ms - 5 * HORA).toISOString().replace('Z', '-05:00')

/** Cita que empieza dentro de `horas`; el límite para reprogramar es ANTELACION h antes. */
function citaEn(horas: number, id = 1, diasLaborales?: number[]): CitaConfirmada {
  const inicio = Date.now() + horas * HORA
  return {
    id,
    estado: 'PENDING',
    servicio: { id: 2, nombre: 'Corte clásico', precio: 25000, duracionMin: 45 },
    barbero: {
      id: 9,
      nombre: 'Thiago',
      rol: 'Master barber',
      calificacion: 4.9,
      diasLaborales,
    },
    inicio: enColombia(inicio),
    total: 25000,
    reprogramarAntes: new Date(inicio - ANTELACION * HORA).toISOString(),
    horasAntelacion: ANTELACION,
  }
}

function mostrar(citas: CitaConfirmada[]) {
  vi.mocked(listarMisCitasApi).mockResolvedValue(citas)
  return render(
    <MemoryRouter>
      <PerfilPage />
    </MemoryRouter>,
  )
}

describe('PerfilPage: gestionar mis citas (HU-03)', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useCitasStore.setState({ citas: [], isLoading: false, error: null })
    useAuthStore.setState({
      accessToken: 'tok',
      user: { id: 5, email: 'cliente@barberflow.test', role: 'cliente' },
      isHydrating: false,
    })
    vi.mocked(listarFranjas).mockResolvedValue([
      { hora: '09:00', disponible: true },
      { hora: '14:30', disponible: true },
    ])
  })

  it('Dado un cliente con citas activas, Cuando abre su perfil, Entonces las ve con estado en español y precio', async () => {
    mostrar([citaEn(72)])

    expect(await screen.findByText(/Corte clásico/)).toBeInTheDocument()
    expect(screen.getByText('Pendiente')).toBeInTheDocument()
    expect(screen.getByText(/25\.000/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /reprogramar/i })).toBeEnabled()
    expect(screen.getByRole('button', { name: /cancelar/i })).toBeInTheDocument()
  })

  it('Dado que no tiene citas, Cuando abre su perfil, Entonces se le avisa y se le invita a reservar', async () => {
    mostrar([])

    expect(await screen.findByText(/No tienes citas programadas/)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /reservar ahora/i })).toHaveAttribute(
      'href',
      '/reservar',
    )
  })

  it('Dado una cita con antelación suficiente, Cuando reprograma, Entonces ve horarios reales del barbero y los reserva', async () => {
    const cita = citaEn(72)
    vi.mocked(reprogramarCitaApi).mockResolvedValue(cita)
    const user = userEvent.setup()
    mostrar([cita])
    await user.click(await screen.findByRole('button', { name: /reprogramar/i }))

    const dialogo = await screen.findByRole('dialog')
    expect(dialogo).toHaveAccessibleName(/reprogramar cita/i)
    await user.click(screen.getAllByRole('button', { pressed: false })[0])

    await waitFor(() => expect(listarFranjas).toHaveBeenCalled())
    const [barberoId, fecha, duracion] = vi.mocked(listarFranjas).mock.calls[0]
    expect(barberoId).toBe(9)
    expect(fecha).toMatch(/^\d{4}-\d{2}-\d{2}$/)
    expect(duracion).toBe(45)

    await user.click(await screen.findByRole('button', { name: 'Hora 14:30' }))
    expect(screen.queryByRole('button', { name: 'Hora 10:00' })).not.toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: /confirmar cambio/i }))

    await waitFor(() => expect(reprogramarCitaApi).toHaveBeenCalled())
    const [citaEnviada, nuevoInicio] = vi.mocked(reprogramarCitaApi).mock.calls[0]
    expect(citaEnviada.id).toBe(cita.id)
    expect(nuevoInicio).toBe(`${fecha}T14:30:00-05:00`)
    expect(await screen.findByText(/cita reprogramada/i)).toBeInTheDocument()
  })

  it('Dado un barbero que no atiende los domingos, Cuando reprograma, Entonces no se ofrece ningún domingo', async () => {
    const user = userEvent.setup()
    mostrar([citaEn(72, 1, [0, 1, 2, 3, 4, 5])])
    await user.click(await screen.findByRole('button', { name: /reprogramar/i }))
    await screen.findByRole('dialog')

    expect(screen.getAllByRole('button', { pressed: false })).toHaveLength(7)
    expect(screen.queryByText(/^dom$/i)).not.toBeInTheDocument()
  })

  it('Dado un día sin horarios libres, Cuando se consulta, Entonces se le avisa y no puede confirmar', async () => {
    vi.mocked(listarFranjas).mockResolvedValue([])
    const user = userEvent.setup()
    mostrar([citaEn(72)])
    await user.click(await screen.findByRole('button', { name: /reprogramar/i }))
    await screen.findByRole('dialog')
    await user.click(screen.getAllByRole('button', { pressed: false })[0])

    expect(await screen.findByText(/No hay horarios disponibles/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /confirmar cambio/i })).toBeDisabled()
  })

  it('Dado que falta menos que la antelación mínima, Cuando ve su cita, Entonces Reprogramar está deshabilitado con la explicación dinámica', async () => {
    mostrar([citaEn(1)])

    expect(await screen.findByRole('button', { name: /reprogramar/i })).toBeDisabled()
    expect(screen.getByText(/Faltan menos de 2 horas/)).toBeInTheDocument()
    expect(screen.queryByText(/12 horas/)).not.toBeInTheDocument()
  })

  it('Dado que falta menos de la antelación, Cuando cancela, Entonces se avisa antes y queda un aviso de éxito con la nota de tardía', async () => {
    vi.mocked(cancelarCitaApi).mockResolvedValue({ tardia: true })
    const user = userEvent.setup()
    mostrar([citaEn(1)])

    await user.click(await screen.findByRole('button', { name: /^cancelar$/i }))
    expect(screen.getByRole('dialog')).toHaveTextContent(/cancelación tardía/)
    await user.click(screen.getByRole('button', { name: /sí, cancelar cita/i }))

    await waitFor(() => expect(cancelarCitaApi).toHaveBeenCalledWith(1))
    const aviso = await screen.findByRole('status')
    expect(aviso).toHaveTextContent(/cita cancelada/i)
    expect(aviso).toHaveTextContent(/cancelación tardía/i)
  })

  it('Dado una cita con antelación suficiente, Cuando la cancela, Entonces el aviso es de éxito sin nota de tardía', async () => {
    vi.mocked(cancelarCitaApi).mockResolvedValue({ tardia: false })
    const user = userEvent.setup()
    mostrar([citaEn(72)])

    await user.click(await screen.findByRole('button', { name: /^cancelar$/i }))
    expect(screen.getByRole('dialog')).not.toHaveTextContent(/cancelación tardía/)
    await user.click(screen.getByRole('button', { name: /sí, cancelar cita/i }))

    const aviso = await screen.findByRole('status')
    expect(aviso).toHaveTextContent(/cita cancelada/i)
    expect(aviso).not.toHaveTextContent(/tardía/i)
    expect(screen.getByText(/No tienes citas programadas/)).toBeInTheDocument()
  })
})
