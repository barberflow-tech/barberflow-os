import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { useAuthStore } from '@/stores/useAuthStore'
import {
  guardarHorarioApi,
  HorarioConflictoError,
  HorariosError,
  obtenerHorarioApi,
  type HorarioSemanal,
} from './horariosApi'

const semana: HorarioSemanal = {
  barber: 3,
  name: 'Santiago Ruiz',
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
  ],
}

const respuesta = (cuerpo: unknown, status = 200) =>
  new Response(JSON.stringify(cuerpo), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })

describe('horariosApi', () => {
  const fetchMock = vi.fn()

  beforeEach(() => {
    vi.stubGlobal('fetch', fetchMock)
    useAuthStore.setState({ accessToken: 'token-admin' })
  })

  afterEach(() => {
    fetchMock.mockReset()
    vi.unstubAllGlobals()
    useAuthStore.setState({ accessToken: null })
  })

  it('Dado un barbero, Cuando el admin consulta su horario, Entonces pide la semana con su token', async () => {
    fetchMock.mockResolvedValue(respuesta(semana))

    const horario = await obtenerHorarioApi(3)

    expect(horario).toEqual(semana)
    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toMatch(/\/api\/v1\/barbers\/3\/schedule$/)
    expect(init.headers.Authorization).toBe('Bearer token-admin')
  })

  it('Dado un turno armado, Cuando se guarda, Entonces hace PUT con la semana completa', async () => {
    fetchMock.mockResolvedValue(respuesta(semana))

    await guardarHorarioApi(3, semana.days)

    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toMatch(/\/api\/v1\/barbers\/3\/schedule$/)
    expect(init.method).toBe('PUT')
    expect(JSON.parse(init.body)).toEqual({ days: semana.days })
  })

  it('Dado un cambio que deja citas fuera del turno, Cuando el backend responde 409, Entonces lanza el conflicto con las citas', async () => {
    const conflicts = [
      {
        appointment: 12,
        start_at: '2026-11-20T17:30:00-05:00',
        reason: 'fuera_de_turno',
      },
    ]
    fetchMock.mockResolvedValue(
      respuesta(
        {
          detail: 'El cambio afecta citas futuras.',
          code: 'horario_con_citas_futuras',
          conflicts,
        },
        409,
      ),
    )

    const error = await guardarHorarioApi(3, semana.days).catch((e: unknown) => e)

    expect(error).toBeInstanceOf(HorarioConflictoError)
    expect((error as HorarioConflictoError).conflictos).toEqual(conflicts)
  })

  it('Dado una sesión sin permisos, Cuando el backend responde 403, Entonces avisa que no puede configurar horarios', async () => {
    fetchMock.mockResolvedValue(respuesta({ detail: 'no' }, 403))

    await expect(obtenerHorarioApi(3)).rejects.toThrow(
      new HorariosError('Tu sesión no permite configurar horarios.'),
    )
  })

  it('Dado un turno inválido, Cuando el backend responde 400, Entonces muestra un mensaje de revisión', async () => {
    fetchMock.mockResolvedValue(respuesta({ days: ['mal'] }, 400))

    await expect(guardarHorarioApi(3, semana.days)).rejects.toThrow(
      /Revisa los horarios/,
    )
  })

  it('Dado que el servidor no responde, Cuando se consulta, Entonces avisa que no hay conexión', async () => {
    fetchMock.mockRejectedValue(new TypeError('fallo de red'))

    await expect(obtenerHorarioApi(3)).rejects.toThrow(/No se pudo conectar/)
  })
})
