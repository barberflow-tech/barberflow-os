import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { useAuthStore } from '@/stores/useAuthStore'
import { crearCita, listarFranjas } from './reservaApi'

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

  it('Dado un token vencido, Cuando pide franjas, Entonces cierra la sesión y repite como visitante', async () => {
    useAuthStore.getState().setSession({
      accessToken: 'vencido',
      user: { id: 1, email: 'a@b.co', role: 'cliente' },
    })
    const fetchMock = vi
      .fn()
      .mockImplementationOnce(() => json({}, 401))
      .mockImplementationOnce(() => json({ available_slots: [] }))
    vi.stubGlobal('fetch', fetchMock)

    await expect(listarFranjas(1, '2099-11-04', 30)).resolves.toEqual([])

    expect(fetchMock).toHaveBeenCalledTimes(2)
    const segunda = fetchMock.mock.calls[1] as unknown as [string, RequestInit?]
    expect(segunda[1]?.headers).toBeUndefined()
    expect(useAuthStore.getState().accessToken).toBeNull()
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

  it('Dado un visitante, Cuando crea la cita, Entonces envía su nombre y celular sin token', async () => {
    useAuthStore.getState().clearSession()
    const fetchMock = vi.fn(() =>
      json(
        {
          id: 5,
          status: 'PENDING',
          start_at: '2099-11-04T14:00:00Z',
          price: '35000.00',
        },
        201,
      ),
    )
    vi.stubGlobal('fetch', fetchMock)

    await crearCita({
      servicioId: 2,
      barberoId: 1,
      inicio: '2099-11-04T09:00:00-05:00',
      contactoNombre: 'Laura Gómez',
      contactoCelular: '3001234567',
    })

    const [, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit]
    expect(JSON.parse(init.body as string)).toMatchObject({
      contact_name: 'Laura Gómez',
      contact_phone: '3001234567',
    })
    expect(init.headers).not.toHaveProperty('Authorization')
  })

  it('Dado el límite de intentos, Cuando se crea la cita, Entonces pide esperar', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() => json({}, 429)),
    )

    await expect(
      crearCita({ servicioId: 2, barberoId: 1, inicio: '2099-11-04T09:00:00-05:00' }),
    ).rejects.toThrow(/Demasiados intentos/)
  })
})
