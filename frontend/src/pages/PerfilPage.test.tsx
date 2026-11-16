import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
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

function citaEn(horas: number, id = 1): CitaConfirmada {
  return {
    id,
    estado: 'PENDING',
    servicio: { id: 2, nombre: 'Corte clásico', precio: 25000, duracionMin: 45 },
    barbero: { id: 9, nombre: 'Thiago', rol: 'Master barber', calificacion: 4.9 },
    inicio: new Date(Date.now() + horas * HORA).toISOString(),
    total: 25000,
  }
}

function mostrar(citas: CitaConfirmada[]) {
  vi.mocked(listarMisCitasApi).mockResolvedValue(citas)
  return render(<PerfilPage />)
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

  it('Dado un cliente con citas activas, Cuando abre su perfil, Entonces las ve listadas', async () => {
    mostrar([citaEn(72)])

    expect(await screen.findByText(/Corte clásico/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Reprogramar' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Cancelar' })).toBeInTheDocument()
  })

  it('Dado que no tiene citas, Cuando abre su perfil, Entonces se le avisa', async () => {
    mostrar([])

    expect(await screen.findByText(/No tienes citas programadas/)).toBeInTheDocument()
  })

  it('Dado una cita con más de 12 h, Cuando pulsa Reprogramar, Entonces ve los horarios reales del barbero y los reserva', async () => {
    const cita = citaEn(72)
    vi.mocked(reprogramarCitaApi).mockResolvedValue({ ...cita, inicio: 'nuevo' })
    const user = userEvent.setup()
    mostrar([cita])
    await user.click(await screen.findByRole('button', { name: 'Reprogramar' }))

    // Pide la disponibilidad del barbero de ESA cita, con la duración de su servicio
    await waitFor(() => expect(listarFranjas).toHaveBeenCalled())
    const [barberoId, fecha, duracion] = vi.mocked(listarFranjas).mock.calls[0]
    expect(barberoId).toBe(9)
    expect(fecha).toMatch(/^\d{4}-\d{2}-\d{2}$/)
    expect(duracion).toBe(45)

    // Y solo ofrece los horarios que devolvió el backend
    const modal = screen.getByText('Reprogramar Cita').closest('div')!.parentElement!
    await user.click(await within(modal.parentElement!).findByText('02:30 PM'))
    expect(within(modal.parentElement!).queryByText('10:00 AM')).not.toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Confirmar Cambio' }))

    // El nuevo horario viaja con la zona de Colombia, como exige el backend
    await waitFor(() => expect(reprogramarCitaApi).toHaveBeenCalled())
    const [citaEnviada, nuevoInicio] = vi.mocked(reprogramarCitaApi).mock.calls[0]
    expect(citaEnviada.id).toBe(cita.id)
    expect(nuevoInicio).toBe(`${fecha}T14:30:00-05:00`)
  })

  it('Dado un día sin horarios libres, Cuando se consulta, Entonces se le avisa', async () => {
    vi.mocked(listarFranjas).mockResolvedValue([])
    const user = userEvent.setup()
    mostrar([citaEn(72)])
    await user.click(await screen.findByRole('button', { name: 'Reprogramar' }))

    expect(await screen.findByText(/No hay horarios disponibles/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Confirmar Cambio' })).toBeDisabled()
  })

  it('Dado una cita con 12 h o menos, Cuando pulsa Reprogramar, Entonces no se permite y se explica por qué', async () => {
    const user = userEvent.setup()
    mostrar([citaEn(5)])

    await user.click(await screen.findByRole('button', { name: 'Reprogramar' }))

    expect(
      await screen.findByText(/No se puede reprogramar la cita con menos de 12 horas/),
    ).toBeInTheDocument()
    expect(listarFranjas).not.toHaveBeenCalled()
  })

  it('Dado una cita con 12 h o menos, Cuando pulsa Cancelar, Entonces se permite avisando que será tardía', async () => {
    vi.mocked(cancelarCitaApi).mockResolvedValue({ tardia: true })
    const user = userEvent.setup()
    mostrar([citaEn(5)])

    await user.click(await screen.findByRole('button', { name: 'Cancelar' }))

    expect(screen.getByText(/se registrará como tardía/)).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Sí, cancelar' }))

    await waitFor(() => expect(cancelarCitaApi).toHaveBeenCalledWith(1))
    expect(await screen.findByText(/cancelación tardía/)).toBeInTheDocument()
  })

  it('Dado una cita con más de 12 h, Cuando la cancela, Entonces desaparece de la lista sin aviso de tardía', async () => {
    vi.mocked(cancelarCitaApi).mockResolvedValue({ tardia: false })
    const user = userEvent.setup()
    mostrar([citaEn(72)])

    await user.click(await screen.findByRole('button', { name: 'Cancelar' }))
    expect(screen.queryByText(/se registrará como tardía/)).not.toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Sí, cancelar' }))

    await waitFor(() =>
      expect(screen.getByText(/No tienes citas programadas/)).toBeInTheDocument(),
    )
    expect(screen.queryByText(/cancelación tardía/)).not.toBeInTheDocument()
  })
})
