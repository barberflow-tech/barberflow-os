import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { useAuthStore } from './useAuthStore'

const sesion = {
  access: 'token-en-memoria',
  user: { id: 1, email: 'ana@barberflow.test', role: 'barbero' },
}

function respuesta(status: number, body: unknown = {}) {
  return Promise.resolve(
    new Response(JSON.stringify(body), {
      status,
      headers: { 'Content-Type': 'application/json' },
    }),
  )
}

describe('useAuthStore', () => {
  beforeEach(() => {
    useAuthStore.setState(useAuthStore.getInitialState(), true)
    localStorage.clear()
    sessionStorage.clear()
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('Dado que la app arranca, Cuando aún no se renovó la sesión, Entonces está hidratando y sin usuario', () => {
    const { isHydrating, user, accessToken } = useAuthStore.getState()

    expect(isHydrating).toBe(true)
    expect(user).toBeNull()
    expect(accessToken).toBeNull()
  })

  it('Dado un usuario autenticado, Cuando recarga la página (F5), Entonces la sesión se renueva con la cookie de refresco', async () => {
    const fetchMock = vi.fn(() => respuesta(200, sesion))
    vi.stubGlobal('fetch', fetchMock)

    await useAuthStore.getState().restoreSession()

    const [url, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit]
    expect(url).toMatch(/\/api\/v1\/auth\/refresh$/)
    expect(init.method).toBe('POST')
    expect(init.credentials).toBe('include')

    const state = useAuthStore.getState()
    expect(state.user).toEqual(sesion.user)
    expect(state.accessToken).toBe(sesion.access)
    expect(state.isHydrating).toBe(false)
  })

  it('Dado que el refresh token no es válido, Cuando se restaura la sesión, Entonces queda como invitado', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() => respuesta(401)),
    )

    await useAuthStore.getState().restoreSession()

    const state = useAuthStore.getState()
    expect(state.user).toBeNull()
    expect(state.accessToken).toBeNull()
    expect(state.isHydrating).toBe(false)
  })

  it('Dado que el backend no responde, Cuando se restaura la sesión, Entonces queda como invitado sin quedarse cargando', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() => Promise.reject(new TypeError('network error'))),
    )

    await useAuthStore.getState().restoreSession()

    const state = useAuthStore.getState()
    expect(state.user).toBeNull()
    expect(state.isHydrating).toBe(false)
  })

  it('Dado una sesión activa, Cuando se guarda, Entonces el access token no se persiste en el navegador', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() => respuesta(200, sesion)),
    )

    await useAuthStore.getState().restoreSession()

    expect(JSON.stringify({ ...localStorage })).not.toContain(sesion.access)
    expect(JSON.stringify({ ...sessionStorage })).not.toContain(sesion.access)
  })

  it('Dado una sesión activa, Cuando se limpia la sesión, Entonces vuelve a invitado', () => {
    useAuthStore.getState().setSession({
      accessToken: sesion.access,
      user: { id: 1, email: sesion.user.email, role: 'barbero' },
    })

    useAuthStore.getState().clearSession()

    const state = useAuthStore.getState()
    expect(state.user).toBeNull()
    expect(state.accessToken).toBeNull()
    expect(state.isHydrating).toBe(false)
  })
})

describe('logout', () => {
  it('Dado un usuario con sesión, Cuando cierra sesión, Entonces avisa al servidor y limpia el estado', async () => {
    const fetchMock = vi.fn(() => Promise.resolve(new Response(null, { status: 204 })))
    vi.stubGlobal('fetch', fetchMock)
    useAuthStore.setState({
      accessToken: 'tok',
      user: { id: 1, email: 'a@b.test', role: 'barbero' },
      isHydrating: false,
    })

    await useAuthStore.getState().logout()

    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining('/api/v1/auth/logout'),
      expect.objectContaining({ method: 'POST', credentials: 'include' }),
    )
    expect(useAuthStore.getState().user).toBeNull()
    expect(useAuthStore.getState().accessToken).toBeNull()
    vi.unstubAllGlobals()
  })

  it('Dado que no hay red, Cuando cierra sesión, Entonces igual limpia el estado local', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() => Promise.reject(new Error('offline'))),
    )
    useAuthStore.setState({
      accessToken: 'tok',
      user: { id: 1, email: 'a@b.test', role: 'barbero' },
      isHydrating: false,
    })

    await useAuthStore.getState().logout()

    expect(useAuthStore.getState().user).toBeNull()
    vi.unstubAllGlobals()
  })
})
