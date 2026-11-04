import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { useAuthStore } from '@/stores/useAuthStore'
import { crearCita, listarFranjas, ReservaError } from './reservaApi'

vi.mock('./catalogoApi', () => ({
  listarServiciosApi: vi.fn().mockResolvedValue([
    {
      id: 2,
      name: 'Corte',
      price: 35000,
      duration_minutes: 40,
      description: '',
      is_active: true,
    },
  ]),
}))

const json = (cuerpo: unknown, status = 200) =>
  Promise.resolve(new Response(JSON.stringify(cuerpo), { status }))

describe('reservaApi con el backend', () => {
  beforeEach(() => {
    useAuthStore.setState({
      accessToken: 'tok-cliente',
      user: { id: 5, email: 'c@b.test', role: 'cliente' },
      isHydrating: false,
    })
  })
  afterEach(() => vi.unstubAllGlobals())

  it('Dado un servicio de 40 min, Cuando pide franjas, Entonces usa bloques de 60 y convierte a hora de Colombia', async () => {
    const futuro = '2099-11-04T14:00:00Z' // 09:00 en Bogotá
    const fetchMock = vi.fn(() =>
      json({
        available_slots: [
          { start_at: futuro, end_at: '2099-11-04T15:00:00Z' },
          { start_at: '2000-01-01T14:00:00Z', end_at: '2000-01-01T15:00:00Z' },
        ],
      }),
    )
    vi.stubGlobal('fetch', fetchMock)

    const franjas = await listarFranjas(1, '2099-11-04', 40)

    const [url, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit]
    expect(url).toContain('barber=1&date=2099-11-04&slot_duration=60')
    expect(init.headers).toMatchObject({ Authorization: 'Bearer tok-cliente' })
    // La franja pasada se descarta y la futura se muestra en hora local.
    expect(franjas).toEqual([{ hora: '09:00', disponible: true }])
  })

  it('Dado un servicio de 30 min, Cuando pide franjas, Entonces usa bloques de 30', async () => {
    const fetchMock = vi.fn(() => json({ available_slots: [] }))
    vi.stubGlobal('fetch', fetchMock)

    await listarFranjas(1, '2099-11-04', 30)

    expect((fetchMock.mock.calls[0] as unknown as [string])[0]).toContain(
      'slot_duration=30',
    )
  })

  it('Dado un visitante sin sesión, Cuando pide franjas, Entonces se le pide iniciar sesión', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() => json({}, 401)),
    )

    await expect(listarFranjas(1, '2099-11-04', 30)).rejects.toMatchObject({
      requiereSesion: true,
    })
  })

  it('Dado un cliente, Cuando crea la cita, Entonces envía POST con barber, service y start_at y devuelve el resumen', async () => {
    const fetchMock = vi.fn(() =>
      json(
        {
          id: 77,
          status: 'PENDING',
          start_at: '2099-11-04T14:00:00Z',
          price: '35000.00',
        },
        201,
      ),
    )
    vi.stubGlobal('fetch', fetchMock)

    const cita = await crearCita({
      servicioId: 2,
      barberoId: 1,
      inicio: '2099-11-04T09:00:00-05:00',
    })

    const [url, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit]
    expect(url).toMatch(/\/api\/v1\/appointments$/)
    expect(JSON.parse(init.body as string)).toEqual({
      barber: 1,
      service: 2,
      start_at: '2099-11-04T09:00:00-05:00',
    })
    expect(cita).toMatchObject({ id: 77, estado: 'PENDING', total: 35000 })
    // 14:00 UTC = 09:00 en Colombia: la pantalla de confirmación debe mostrar esa hora.
    expect(cita.inicio).toBe('2099-11-04T09:00:00-05:00')
    expect(cita.servicio.nombre).toBe('Corte')
  })

  it('Dado que otra persona tomó la franja, Cuando se crea la cita, Entonces avisa del conflicto', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() => json({ detail: 'x' }, 409)),
    )

    await expect(
      crearCita({ servicioId: 2, barberoId: 1, inicio: '2099-11-04T09:00:00-05:00' }),
    ).rejects.toThrow(/acaba de ocupar/)
  })

  it('Dado un 401, Cuando se crea la cita, Entonces pide iniciar sesión', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() => json({}, 401)),
    )

    const error = await crearCita({
      servicioId: 2,
      barberoId: 1,
      inicio: '2099-11-04T09:00:00-05:00',
    }).catch((e: unknown) => e)

    expect(error).toBeInstanceOf(ReservaError)
    expect((error as ReservaError).requiereSesion).toBe(true)
  })
})
