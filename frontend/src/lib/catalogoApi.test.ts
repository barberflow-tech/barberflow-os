import { afterEach, describe, expect, it, vi } from 'vitest'
import { CatalogoError, listarServiciosApi } from './catalogoApi'

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
