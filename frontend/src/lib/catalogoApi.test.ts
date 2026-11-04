import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { useAuthStore } from '@/stores/useAuthStore'
import {
  actualizarServicioApi,
  CatalogoError,
  crearServicioApi,
  eliminarServicioApi,
  listarServiciosApi,
} from './catalogoApi'

afterEach(() => vi.unstubAllGlobals())

describe('listarServiciosApi', () => {
  it('Dado un backend con servicios, Cuando se listan, Entonces convierte el precio decimal a número', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => [
          {
            id: 1,
            name: 'Corte',
            price: '35000.00',
            duration_minutes: 30,
            is_active: true,
          },
        ],
      }),
    )
    const servicios = await listarServiciosApi()
    expect(servicios[0].price).toBe(35000)
    expect(fetch).toHaveBeenCalledWith(expect.stringMatching(/\/api\/v1\/services$/))
  })

  it('Dado un backend caído, Cuando se listan, Entonces lanza un error legible', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('fail')))
    await expect(listarServiciosApi()).rejects.toBeInstanceOf(CatalogoError)
  })

  it('Dado un 500, Cuando se listan, Entonces lanza un error legible', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 500 }))
    await expect(listarServiciosApi()).rejects.toThrow('No se pudieron cargar')
  })
})

describe('CRUD de servicios (admin)', () => {
  const entrada = {
    name: 'Fade',
    price: 45000,
    duration_minutes: 40,
    description: '',
    is_active: true,
  }

  beforeEach(() => {
    useAuthStore.setState({
      accessToken: 'tok-admin',
      user: { id: 1, email: 'a@b.test', role: 'admin' },
      isHydrating: false,
    })
  })

  afterEach(() => vi.unstubAllGlobals())

  it('Dado un admin, Cuando crea un servicio, Entonces envía POST con el token y convierte el precio', async () => {
    const fetchMock = vi.fn(() =>
      Promise.resolve(
        new Response(JSON.stringify({ id: 5, ...entrada, price: '45000.00' }), {
          status: 201,
        }),
      ),
    )
    vi.stubGlobal('fetch', fetchMock)

    const creado = await crearServicioApi(entrada)

    expect(creado.price).toBe(45000)
    const [url, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit]
    expect(url).toMatch(/\/api\/v1\/services$/)
    expect(init.method).toBe('POST')
    expect(init.headers).toMatchObject({ Authorization: 'Bearer tok-admin' })
  })

  it('Dado un 403, Cuando edita, Entonces explica que solo un administrador puede', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() => Promise.resolve(new Response('{}', { status: 403 }))),
    )

    await expect(actualizarServicioApi(5, entrada)).rejects.toThrow(
      'Solo un administrador puede modificar el catálogo.',
    )
  })

  it('Dado un 400 de validación, Cuando crea, Entonces muestra el mensaje del campo', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() =>
        Promise.resolve(
          new Response(
            JSON.stringify({
              price: ['Ensure this value is greater than or equal to 0.'],
            }),
            {
              status: 400,
            },
          ),
        ),
      ),
    )

    await expect(crearServicioApi(entrada)).rejects.toThrow(/price: Ensure this value/)
  })

  it('Dado un servicio, Cuando se elimina, Entonces envía DELETE a su id', async () => {
    const fetchMock = vi.fn(() => Promise.resolve(new Response(null, { status: 204 })))
    vi.stubGlobal('fetch', fetchMock)

    await eliminarServicioApi(5)

    const [url, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit]
    expect(url).toMatch(/\/api\/v1\/services\/5$/)
    expect(init.method).toBe('DELETE')
  })

  it('Dado el público, Cuando lista, Entonces no envía la sesión (no ve inactivos)', async () => {
    const fetchMock = vi.fn(() => Promise.resolve(new Response('[]', { status: 200 })))
    vi.stubGlobal('fetch', fetchMock)

    await listarServiciosApi()

    expect(fetchMock.mock.calls[0]).toHaveLength(1)
  })
})
