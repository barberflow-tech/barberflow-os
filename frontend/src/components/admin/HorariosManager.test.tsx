import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { listarBarberosApi } from '@/lib/barberosApi'
import {
  guardarHorarioApi,
  HorarioConflictoError,
  obtenerHorarioApi,
  type HorarioSemanal,
} from '@/lib/horariosApi'
import { useAuthStore } from '@/stores/useAuthStore'
import { HorariosManager } from './HorariosManager'

vi.mock('@/lib/barberosApi', () => ({
  listarBarberosApi: vi.fn(),
}))
vi.mock('@/lib/horariosApi', async (importOriginal) => ({
  ...(await importOriginal<typeof import('@/lib/horariosApi')>()),
  obtenerHorarioApi: vi.fn(),
  guardarHorarioApi: vi.fn(),
}))

const horarioDe = (barber: number, name: string): HorarioSemanal => ({
  barber,
  name,
  timezone: 'America/Bogota',
  updated_at: null,
  days: [
    {
      weekday: 0,
      open_time: '09:00',
      close_time: '18:00',
      break_start: '13:00',
      break_duration_minutes: 60,
    },
    {
      weekday: 1,
      open_time: '09:00',
      close_time: '18:00',
      break_start: null,
      break_duration_minutes: null,
    },
  ],
})

const renderizar = () =>
  render(
    <MemoryRouter>
      <HorariosManager />
    </MemoryRouter>,
  )

const dia = (nombre: string) => screen.getByRole('group', { name: nombre })

describe('HorariosManager', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useAuthStore.setState({
      user: { id: 1, email: 'admin@barberflow.co', role: 'admin' },
    } as never)
    vi.mocked(listarBarberosApi).mockResolvedValue([
      { id: 3, name: 'Santiago Ruiz', servicios: [1] },
      { id: 4, name: 'Andrés Mora', servicios: [1] },
    ])
    vi.mocked(obtenerHorarioApi).mockImplementation(async (id: number) =>
      id === 3
        ? horarioDe(3, 'Santiago Ruiz')
        : {
            ...horarioDe(4, 'Andrés Mora'),
            days: [
              {
                weekday: 5,
                open_time: '08:00',
                close_time: '15:00',
                break_start: null,
                break_duration_minutes: null,
              },
            ],
          },
    )
    vi.mocked(guardarHorarioApi).mockImplementation(async (id, days) => ({
      ...horarioDe(id, 'Santiago Ruiz'),
      days,
    }))
  })

  it('Dado un barbero con turno guardado, Cuando el admin abre la vista, Entonces ve su semana con turnos y descansos', async () => {
    renderizar()

    expect(await screen.findByLabelText('Barbero')).toHaveValue('3')
    const lunes = await screen.findByRole('group', { name: 'Lunes' })
    expect(within(lunes).getByLabelText('Apertura')).toHaveValue('09:00')
    expect(within(lunes).getByLabelText('Cierre')).toHaveValue('18:00')
    expect(within(lunes).getByLabelText('Inicio del descanso')).toHaveValue('13:00')
    expect(within(lunes).getByLabelText('Duración del descanso (min)')).toHaveValue(60)
    expect(within(dia('Martes')).queryByLabelText('Inicio del descanso')).toBeNull()
    expect(within(dia('Jueves')).getByText('Cerrado')).toBeInTheDocument()
  })

  it('Dado otro barbero, Cuando el admin lo elige, Entonces carga el horario de ese barbero', async () => {
    renderizar()
    await screen.findByRole('group', { name: 'Lunes' })

    await userEvent.selectOptions(screen.getByLabelText('Barbero'), '4')

    expect(obtenerHorarioApi).toHaveBeenLastCalledWith(4)
    const sabado = await screen.findByRole('group', { name: 'Sábado' })
    expect(within(sabado).getByLabelText('Apertura')).toHaveValue('08:00')
    expect(within(dia('Lunes')).getByText('Cerrado')).toBeInTheDocument()
  })

  it('Dado un día abierto, Cuando lo marca cerrado y guarda, Entonces el PUT omite ese día', async () => {
    renderizar()
    await screen.findByRole('group', { name: 'Lunes' })

    await userEvent.click(
      within(dia('Martes')).getByRole('button', { name: 'Marcar cerrado' }),
    )
    await userEvent.click(screen.getByRole('button', { name: 'Guardar horario' }))

    expect(guardarHorarioApi).toHaveBeenCalledWith(3, [
      {
        weekday: 0,
        open_time: '09:00',
        close_time: '18:00',
        break_start: '13:00',
        break_duration_minutes: 60,
      },
    ])
    expect(await screen.findByText('Horario guardado')).toBeInTheDocument()
  })

  it('Dado un día cerrado, Cuando lo abre y define turno con descanso, Entonces el PUT lo incluye', async () => {
    renderizar()
    await screen.findByRole('group', { name: 'Lunes' })

    const jueves = dia('Jueves')
    await userEvent.click(within(jueves).getByRole('button', { name: 'Abrir día' }))
    const apertura = within(jueves).getByLabelText('Apertura')
    await userEvent.clear(apertura)
    await userEvent.type(apertura, '10:00')
    const cierre = within(jueves).getByLabelText('Cierre')
    await userEvent.clear(cierre)
    await userEvent.type(cierre, '19:00')
    await userEvent.click(
      within(jueves).getByRole('button', { name: 'Añadir descanso' }),
    )
    await userEvent.click(screen.getByRole('button', { name: 'Guardar horario' }))

    const [, enviados] = vi.mocked(guardarHorarioApi).mock.calls[0]
    expect(enviados).toContainEqual({
      weekday: 3,
      open_time: '10:00',
      close_time: '19:00',
      break_start: '13:00',
      break_duration_minutes: 60,
    })
  })

  it('Dado un día con descanso, Cuando lo quita y guarda, Entonces el día se envía sin descanso', async () => {
    renderizar()
    await screen.findByRole('group', { name: 'Lunes' })

    await userEvent.click(
      within(dia('Lunes')).getByRole('button', { name: 'Quitar descanso' }),
    )
    await userEvent.click(screen.getByRole('button', { name: 'Guardar horario' }))

    const [, enviados] = vi.mocked(guardarHorarioApi).mock.calls[0]
    expect(enviados[0]).toMatchObject({
      weekday: 0,
      break_start: null,
      break_duration_minutes: null,
    })
  })

  it('Dado un cierre anterior a la apertura, Cuando intenta guardar, Entonces avisa y no llama al backend', async () => {
    renderizar()
    await screen.findByRole('group', { name: 'Lunes' })

    const cierre = within(dia('Lunes')).getByLabelText('Cierre')
    await userEvent.clear(cierre)
    await userEvent.type(cierre, '08:00')
    await userEvent.click(screen.getByRole('button', { name: 'Guardar horario' }))

    expect(await screen.findByRole('alert')).toHaveTextContent(
      /Lunes.*cierre.*posterior/i,
    )
    expect(guardarHorarioApi).not.toHaveBeenCalled()
  })

  it('Dado un descanso fuera del turno, Cuando intenta guardar, Entonces avisa y no llama al backend', async () => {
    renderizar()
    await screen.findByRole('group', { name: 'Lunes' })

    const inicio = within(dia('Lunes')).getByLabelText('Inicio del descanso')
    await userEvent.clear(inicio)
    await userEvent.type(inicio, '17:30')
    await userEvent.click(screen.getByRole('button', { name: 'Guardar horario' }))

    expect(await screen.findByRole('alert')).toHaveTextContent(/Lunes.*descanso/i)
    expect(guardarHorarioApi).not.toHaveBeenCalled()
  })

  it('Dado un cambio que deja citas fuera del turno, Cuando el backend responde 409, Entonces lista las citas en conflicto', async () => {
    vi.mocked(guardarHorarioApi).mockRejectedValue(
      new HorarioConflictoError('El cambio afecta citas futuras.', [
        {
          appointment: 12,
          start_at: '2026-11-20T17:30:00-05:00',
          reason: 'fuera_de_turno',
        },
      ]),
    )
    renderizar()
    await screen.findByRole('group', { name: 'Lunes' })

    await userEvent.click(screen.getByRole('button', { name: 'Guardar horario' }))

    const aviso = await screen.findByRole('alert')
    expect(aviso).toHaveTextContent(/citas futuras/i)
    expect(aviso).toHaveTextContent(/Cita #12/)
    expect(aviso).toHaveTextContent(/5:30/)
    expect(screen.queryByText('Horario guardado')).toBeNull()
  })

  it('Dado un error del servidor, Cuando falla la carga de barberos, Entonces muestra el mensaje', async () => {
    vi.mocked(listarBarberosApi).mockRejectedValue(
      new Error('No se pudieron cargar los barberos.'),
    )
    renderizar()

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'No se pudieron cargar los barberos.',
    )
  })
})
