import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { CitaConfirmada, CitaHistorial } from '@/lib/reservaApi'
import { useAuthStore } from '@/stores/useAuthStore'
import { useCitasStore } from '@/stores/useCitasStore'
import { PerfilPage } from './PerfilPage'

vi.mock('@/lib/reservaApi', async (importOriginal) => {
  const real = await importOriginal<typeof import('@/lib/reservaApi')>()
  return {
    ReservaError: real.ReservaError,
    listarMisCitasApi: vi.fn(),
    listarCitasCanceladasApi: vi.fn(),
    cancelarCitaApi: vi.fn(),
    reprogramarCitaApi: vi.fn(),
    listarFranjas: vi.fn(),
  }
})

import {
  cancelarCitaApi,
  listarCitasCanceladasApi,
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
    useCitasStore.setState({
      citas: [],
      isLoading: false,
      error: null,
      canceladas: [],
      cargandoCanceladas: false,
      errorCanceladas: null,
    })
    vi.mocked(listarCitasCanceladasApi).mockResolvedValue([])
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

  describe('cita afectada por un bloqueo', () => {
    it('Dado una cita afectada, Cuando el cliente ve sus citas, Entonces se le avisa que el barbero no podrá atenderla', async () => {
      mostrar([{ ...citaEn(72, 1), afectadaPorBloqueo: true }])

      const aviso = await screen.findByTestId('cita-afectada')
      expect(aviso).toHaveTextContent(/no podrá atenderte/i)
      expect(aviso).toHaveTextContent(/reprograma/i)
    })

    it('Dado una cita sin bloqueo, Cuando el cliente ve sus citas, Entonces no aparece el aviso', async () => {
      mostrar([citaEn(72, 1)])

      await screen.findByText('Pendiente')
      expect(screen.queryByTestId('cita-afectada')).toBeNull()
    })

    it('Dado una cita afectada, Cuando la reprograma, Entonces deja de estar marcada', async () => {
      vi.mocked(reprogramarCitaApi).mockResolvedValue(citaEn(96, 1))
      const user = userEvent.setup()
      mostrar([{ ...citaEn(72, 1), afectadaPorBloqueo: true }])
      await screen.findByTestId('cita-afectada')

      await user.click(screen.getByRole('button', { name: /reprogramar/i }))
      await screen.findByRole('dialog')
      await user.click(screen.getAllByRole('button', { pressed: false })[0])
      await user.click(await screen.findByRole('button', { name: 'Hora 14:30' }))
      await user.click(screen.getByRole('button', { name: /confirmar cambio/i }))

      await waitFor(() => expect(screen.queryByTestId('cita-afectada')).toBeNull())
    })
  })

  describe('citas canceladas', () => {
    const canceladaPor = (
      motivo: CitaHistorial['motivo'],
      id: number,
      extra: Partial<CitaHistorial> = {},
    ): CitaHistorial => ({
      ...citaEn(-48, id),
      estado: motivo === 'cancelled' ? 'CANCELLED' : 'PENDING',
      motivo,
      tardia: false,
      ...extra,
    })

    it('Dado una cita cancelada y otra vencida, Cuando abre «Canceladas», Entonces ve cada una con su motivo', async () => {
      vi.mocked(listarCitasCanceladasApi).mockResolvedValue([
        canceladaPor('cancelled', 1, { canceladaEn: '2026-11-18T12:00:00Z' }),
        canceladaPor('expired', 2),
      ])
      const user = userEvent.setup()
      mostrar([])

      await user.click(await screen.findByRole('tab', { name: /canceladas/i }))

      expect(await screen.findByText('Cancelada por ti')).toBeInTheDocument()
      expect(screen.getByText('Vencida')).toBeInTheDocument()
      expect(screen.getByText(/la hora pasó sin que se atendiera/i)).toBeInTheDocument()
      expect(screen.getAllByText('Corte clásico')).toHaveLength(2)
    })

    it('Dado una cancelación tardía, Cuando abre «Canceladas», Entonces se le indica que fue tardía', async () => {
      vi.mocked(listarCitasCanceladasApi).mockResolvedValue([
        canceladaPor('cancelled', 1, {
          canceladaEn: '2026-11-18T12:00:00Z',
          tardia: true,
        }),
      ])
      const user = userEvent.setup()
      mostrar([])

      await user.click(await screen.findByRole('tab', { name: /canceladas/i }))

      expect(await screen.findByText(/cancelación tardía/i)).toBeInTheDocument()
    })

    it('Dado que no tiene canceladas, Cuando abre «Canceladas», Entonces se le avisa', async () => {
      const user = userEvent.setup()
      mostrar([])

      await user.click(await screen.findByRole('tab', { name: /canceladas/i }))

      expect(await screen.findByText(/No tienes citas canceladas/)).toBeInTheDocument()
    })

    it('Dado una cita cancelada, Cuando está en «Próximas», Entonces no se mezcla con las citas activas', async () => {
      vi.mocked(listarCitasCanceladasApi).mockResolvedValue([
        canceladaPor('cancelled', 7),
      ])
      mostrar([citaEn(72, 1)])

      expect(await screen.findByText('Pendiente')).toBeInTheDocument()
      expect(screen.queryByText('Cancelada por ti')).toBeNull()
    })

    it('Dado que cancela una cita, Cuando termina, Entonces aparece en «Canceladas»', async () => {
      vi.mocked(cancelarCitaApi).mockResolvedValue({ tardia: false })
      const user = userEvent.setup()
      mostrar([citaEn(72)])

      await user.click(await screen.findByRole('button', { name: /^cancelar$/i }))
      vi.mocked(listarCitasCanceladasApi).mockResolvedValue([
        canceladaPor('cancelled', 1, { canceladaEn: '2026-11-18T12:00:00Z' }),
      ])
      await user.click(screen.getByRole('button', { name: /sí, cancelar cita/i }))
      await screen.findByRole('status')

      await user.click(screen.getByRole('tab', { name: /canceladas/i }))

      expect(await screen.findByText('Cancelada por ti')).toBeInTheDocument()
    })

    it('Dado que falla la carga de canceladas, Cuando abre «Canceladas», Entonces muestra el error', async () => {
      vi.mocked(listarCitasCanceladasApi).mockRejectedValue(
        new Error('No se pudieron cargar tus citas canceladas.'),
      )
      const user = userEvent.setup()
      mostrar([])

      await user.click(await screen.findByRole('tab', { name: /canceladas/i }))

      expect(await screen.findByRole('alert')).toHaveTextContent(
        'No se pudieron cargar tus citas canceladas.',
      )
    })
  })

  describe('saludo de bienvenida', () => {
    const aLas = (hora: number) => {
      vi.useFakeTimers({ toFake: ['Date'] })
      vi.setSystemTime(new Date(2026, 10, 17, hora, 0))
    }
    const conNombre = (fullName?: string) =>
      useAuthStore.setState({
        user: { id: 5, email: 'cliente@barberflow.test', role: 'cliente', fullName },
      })

    afterEach(() => {
      vi.useRealTimers()
    })

    it('Dado un cliente registrado con nombre, Cuando abre su perfil de mañana, Entonces lo saluda por su primer nombre y no muestra el correo', async () => {
      aLas(9)
      conNombre('Ana Pérez')
      mostrar([])

      expect(await screen.findByText(/Buenos días, Ana/)).toBeInTheDocument()
      expect(screen.queryByText(/cliente@barberflow\.test/)).toBeNull()
    })

    it('Dado un cliente con nombre, Cuando abre su perfil de tarde, Entonces el saludo es «Buenas tardes»', async () => {
      aLas(15)
      conNombre('Ana Pérez')
      mostrar([])

      expect(await screen.findByText(/Buenas tardes, Ana/)).toBeInTheDocument()
    })

    it('Dado un cliente con nombre, Cuando abre su perfil de noche, Entonces el saludo es «Buenas noches»', async () => {
      aLas(21)
      conNombre('Ana Pérez')
      mostrar([])

      expect(await screen.findByText(/Buenas noches, Ana/)).toBeInTheDocument()
    })

    it('Dado un cliente sin nombre guardado, Cuando abre su perfil, Entonces el saludo no inventa un nombre ni muestra el correo', async () => {
      aLas(9)
      conNombre(undefined)
      mostrar([])

      expect(await screen.findByText(/Buenos días/)).toBeInTheDocument()
      expect(screen.queryByText(/undefined/)).toBeNull()
      expect(screen.queryByText(/cliente@barberflow\.test/)).toBeNull()
    })
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
