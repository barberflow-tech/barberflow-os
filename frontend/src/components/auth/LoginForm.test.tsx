import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { useAuthStore } from '@/stores/useAuthStore'
import { LoginForm } from './LoginForm'

const sesion = {
  access: 'token-en-memoria',
  user: { id: 7, email: 'ana@barberflow.test', role: 'cliente' },
}

function respuesta(status: number, body: unknown = {}) {
  return Promise.resolve(
    new Response(JSON.stringify(body), {
      status,
      headers: { 'Content-Type': 'application/json' },
    }),
  )
}

async function completarLogin(email: string, password: string) {
  const user = userEvent.setup()
  await user.type(screen.getByPlaceholderText('hola@thiagobarber.co'), email)
  await user.type(screen.getByPlaceholderText('Mínimo 8 caracteres'), password)
  await user.click(screen.getByRole('button', { name: /Ingresar a BarberFlow/i }))
}

describe('LoginForm', () => {
  beforeEach(() => {
    useAuthStore.setState(useAuthStore.getInitialState(), true)
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('Dado un email inválido, Cuando presiona "Ingresar", Entonces muestra el error inline sin llamar a la API', async () => {
    const fetchMock = vi.fn()
    vi.stubGlobal('fetch', fetchMock)
    render(<LoginForm />)

    await completarLogin('no-es-un-correo', 'Clave-segura-1')

    expect(
      await screen.findByText('Ingrese un correo electrónico válido'),
    ).toBeInTheDocument()
    expect(fetchMock).not.toHaveBeenCalled()
  })

  it('Dado una contraseña de menos de 8 caracteres, Cuando presiona "Ingresar", Entonces muestra el error inline sin llamar a la API', async () => {
    const fetchMock = vi.fn()
    vi.stubGlobal('fetch', fetchMock)
    render(<LoginForm />)

    await completarLogin('ana@barberflow.test', '1234567')

    expect(
      await screen.findByText('La contraseña debe tener al menos 8 caracteres'),
    ).toBeInTheDocument()
    expect(fetchMock).not.toHaveBeenCalled()
  })

  it('Dado credenciales válidas, Cuando inicia sesión, Entonces la sesión queda guardada en Zustand', async () => {
    const fetchMock = vi.fn(() => respuesta(200, sesion))
    vi.stubGlobal('fetch', fetchMock)
    render(<LoginForm />)

    await completarLogin('ana@barberflow.test', 'Clave-segura-1')

    await waitFor(() => expect(useAuthStore.getState().user).toEqual(sesion.user))
    expect(useAuthStore.getState().accessToken).toBe('token-en-memoria')
    expect(useAuthStore.getState().isHydrating).toBe(false)

    const [url, opciones] = fetchMock.mock.calls[0] as unknown as [string, RequestInit]
    expect(url).toMatch(/\/api\/v1\/auth\/login$/)
    expect(opciones.method).toBe('POST')
    expect(opciones.credentials).toBe('include')
    expect(JSON.parse(opciones.body as string)).toEqual({
      email: 'ana@barberflow.test',
      password: 'Clave-segura-1',
    })
  })

  it('Dado credenciales incorrectas, Cuando inicia sesión, Entonces muestra el error y no crea sesión', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() => respuesta(401, { detail: 'No active account' })),
    )
    render(<LoginForm />)

    await completarLogin('ana@barberflow.test', 'Clave-incorrecta')

    expect(
      await screen.findByText('Correo o contraseña incorrectos'),
    ).toBeInTheDocument()
    expect(useAuthStore.getState().user).toBeNull()
    expect(useAuthStore.getState().accessToken).toBeNull()
  })

  it('Dado que el servidor no responde, Cuando inicia sesión, Entonces avisa que no hay conexión', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() => Promise.reject(new TypeError('Failed to fetch'))),
    )
    render(<LoginForm />)

    await completarLogin('ana@barberflow.test', 'Clave-segura-1')

    expect(
      await screen.findByText(/No se pudo conectar con el servidor/i),
    ).toBeInTheDocument()
    expect(useAuthStore.getState().user).toBeNull()
  })

  it('Dado un login en curso, Cuando aún no responde la API, Entonces el botón queda deshabilitado', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() => new Promise(() => {})),
    )
    render(<LoginForm />)

    await completarLogin('ana@barberflow.test', 'Clave-segura-1')

    const boton = await screen.findByRole('button', { name: /Cargando/i })
    expect(boton).toBeDisabled()
  })
})
