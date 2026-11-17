import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { MENSAJE_SIN_CONEXION } from '@/lib/mensajes'
import { useAuthStore } from '@/stores/useAuthStore'
import { listarCitasCanceladasApi, ReservaError } from './reservaApi'

const respuesta = (cuerpo: unknown, status = 200) =>
  new Response(JSON.stringify(cuerpo), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })

const servicio = {
  id: 2,
  name: 'Corte clásico',
  price: 25000,
  duration_minutes: 40,
  description: '',
}
const barbero = { id: 9, name: 'Thiago', working_days: [0, 1] }

describe('listarCitasCanceladasApi', () => {
  const fetchMock = vi.fn()

  beforeEach(() => {
    vi.stubGlobal('fetch', fetchMock)
    useAuthStore.setState({ accessToken: 'tok' })
  })

  afterEach(() => {
    fetchMock.mockReset()
    vi.unstubAllGlobals()
    useAuthStore.setState({ accessToken: null })
  })

  it('Dado una cita cancelada y otra vencida, Cuando se listan, Entonces llegan con su motivo y la hora de Colombia', async () => {
    fetchMock.mockResolvedValue(
      respuesta([
        {
          id: 1,
          status: 'CANCELLED',
          outcome: 'cancelled',
          start_at: '2026-11-20T15:00:00Z',
          end_at: '2026-11-20T15:40:00Z',
          price: '25000.00',
          service: servicio,
          barber: barbero,
          cancelled_at: '2026-11-18T12:00:00Z',
          late_cancellation: true,
        },
        {
          id: 2,
          status: 'PENDING',
          outcome: 'expired',
          start_at: '2026-11-10T15:00:00Z',
          end_at: '2026-11-10T15:40:00Z',
          price: '25000.00',
          service: servicio,
          barber: barbero,
          cancelled_at: null,
          late_cancellation: false,
        },
      ]),
    )

    const citas = await listarCitasCanceladasApi()

    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toMatch(/\/api\/v1\/appointments\/history$/)
    expect(init.headers.Authorization).toBe('Bearer tok')
    expect(citas).toHaveLength(2)
    expect(citas[0]).toMatchObject({
      id: 1,
      motivo: 'cancelled',
      tardia: true,
      inicio: '2026-11-20T10:00:00-05:00',
      canceladaEn: '2026-11-18T12:00:00Z',
      servicio: { nombre: 'Corte clásico', duracionMin: 40 },
      barbero: { nombre: 'Thiago' },
      total: 25000,
    })
    expect(citas[1]).toMatchObject({ id: 2, motivo: 'expired', tardia: false })
    expect(citas[1].canceladaEn).toBeUndefined()
  })

  it('Dado que el backend falla, Cuando se listan, Entonces avisa que no se pudieron cargar', async () => {
    fetchMock.mockResolvedValue(respuesta({ detail: 'boom' }, 500))

    await expect(listarCitasCanceladasApi()).rejects.toThrow(
      new ReservaError('No se pudieron cargar tus citas canceladas.'),
    )
  })

  it('Dado que no hay conexión, Cuando se listan, Entonces muestra el mensaje amigable de conexión', async () => {
    fetchMock.mockRejectedValue(new TypeError('Failed to fetch'))

    await expect(listarCitasCanceladasApi()).rejects.toThrow(MENSAJE_SIN_CONEXION)
  })
})
