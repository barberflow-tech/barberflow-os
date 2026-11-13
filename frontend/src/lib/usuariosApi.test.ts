import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { useAuthStore } from '@/stores/useAuthStore'
import { cambiarRolApi, listarUsuariosApi, UsuariosError } from './usuariosApi'

const fetchMock = vi.fn()

const respuesta = (status: number, cuerpo: unknown) =>
  new Response(JSON.stringify(cuerpo), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })

describe('usuariosApi', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', fetchMock)
    fetchMock.mockReset()
    useAuthStore.setState({ accessToken: 'token-admin' })
  })
  afterEach(() => vi.unstubAllGlobals())

  it('Dado un admin, Cuando lista usuarios, Entonces envía su token a /api/v1/users', async () => {
    fetchMock.mockResolvedValue(respuesta(200, []))

    await listarUsuariosApi()

    const [url, opciones] = fetchMock.mock.calls[0]
    expect(url).toMatch(/\/api\/v1\/users$/)
    expect(opciones.headers).toEqual({ Authorization: 'Bearer token-admin' })
  })

  it('Dado un correo, Cuando busca, Entonces lo envía codificado en ?email=', async () => {
    fetchMock.mockResolvedValue(respuesta(200, []))

    await listarUsuariosApi('ana+1@correo.com')

    expect(fetchMock.mock.calls[0][0]).toMatch(
      /\/api\/v1\/users\?email=ana%2B1%40correo\.com$/,
    )
  })

  it('Dado un cambio de rol, Cuando se guarda, Entonces hace PATCH con el rol en JSON', async () => {
    fetchMock.mockResolvedValue(
      respuesta(200, {
        id: 2,
        email: 'ana@norte.com',
        full_name: '',
        role: 'barbero',
        en_barberia: true,
      }),
    )

    const usuario = await cambiarRolApi(2, 'barbero')

    const [url, opciones] = fetchMock.mock.calls[0]
    expect(url).toMatch(/\/api\/v1\/users\/2\/role$/)
    expect(opciones.method).toBe('PATCH')
    expect(JSON.parse(opciones.body)).toEqual({ role: 'barbero' })
    expect(usuario.role).toBe('barbero')
  })

  it.each([
    [
      400,
      { detail: 'No puedes cambiar tu propio rol.' },
      'No puedes cambiar tu propio rol.',
    ],
    [403, { detail: 'x' }, 'Solo un administrador puede cambiar roles.'],
    [404, { detail: 'x' }, 'El usuario ya no existe o no pertenece a tu barbería.'],
    [
      409,
      { detail: 'Tu cuenta de administrador no pertenece a ninguna barberia.' },
      'Tu cuenta de administrador no pertenece a ninguna barberia.',
    ],
  ])(
    'Dado un %i del backend, Cuando cambia un rol, Entonces lanza un error legible',
    async (status, cuerpo, mensaje) => {
      fetchMock.mockResolvedValue(respuesta(status, cuerpo))

      await expect(cambiarRolApi(2, 'admin')).rejects.toThrow(
        new UsuariosError(mensaje),
      )
    },
  )

  it('Dado que el servidor no responde, Cuando lista, Entonces lanza un error de conexión', async () => {
    fetchMock.mockRejectedValue(new TypeError('Failed to fetch'))

    await expect(listarUsuariosApi()).rejects.toThrow(
      'No se pudo conectar con el servidor.',
    )
  })
})
