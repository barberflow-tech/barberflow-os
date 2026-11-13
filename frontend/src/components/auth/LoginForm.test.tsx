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

  async function completarRegistro(nombre: string, email: string, password: string) {
    const user = userEvent.setup()
    await user.click(screen.getByRole('button', { name: 'Registrarme' }))
    await user.type(screen.getByPlaceholderText('Ej. Thiago Angulo'), nombre)
    await user.type(screen.getByPlaceholderText('hola@thiagobarber.co'), email)
    await user.type(screen.getByPlaceholderText('Mínimo 8 caracteres'), password)
    await user.click(screen.getByRole('button', { name: /Crear mi cuenta/i }))
  }

  it('Dado datos válidos, Cuando se registra, Entonces crea la cuenta en el backend y vuelve al login con aviso', async () => {
    const fetchMock = vi.fn(() =>
      respuesta(201, { id: 9, email: 'nuevo@barberflow.test', role: 'cliente' }),
    )
    vi.stubGlobal('fetch', fetchMock)
    render(<LoginForm />)

    await completarRegistro('Ana Pérez', 'nuevo@barberflow.test', 'Clave-segura-1')

    expect(await screen.findByText(/Cuenta creada con éxito/)).toBeInTheDocument()
    const [url, opciones] = fetchMock.mock.calls[0] as unknown as [string, RequestInit]
    expect(url).toMatch(/\/api\/v1\/auth\/register$/)
    expect(JSON.parse(opciones.body as string)).toEqual({
      fullName: 'Ana Pérez',
      email: 'nuevo@barberflow.test',
      password: 'Clave-segura-1',
    })
    // El registro no inicia sesión: el usuario debe ingresar con su cuenta.
    expect(useAuthStore.getState().user).toBeNull()
  })

  it('Dado un correo ya registrado, Cuando se registra, Entonces muestra el mensaje del servidor y no cambia de vista', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() => respuesta(400, { email: ['Ya existe una cuenta con este correo.'] })),
    )
    render(<LoginForm />)

    await completarRegistro('Ana Pérez', 'ana@barberflow.test', 'Clave-segura-1')

    expect(
      await screen.findByText('Ya existe una cuenta con este correo.'),
    ).toBeInTheDocument()
    expect(screen.queryByText(/Cuenta creada con éxito/)).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Crear mi cuenta/i })).toBeEnabled()
  })

  it('Dado un correo, Cuando pide recuperar la contraseña, Entonces llama al backend y muestra "Revisa tu correo"', async () => {
    const fetchMock = vi.fn(() => respuesta(202, { detail: 'ok' }))
    vi.stubGlobal('fetch', fetchMock)
    const user = userEvent.setup()
    render(<LoginForm />)

    await user.click(
      screen.getByRole('button', { name: /¿Olvidaste tu contraseña\?/i }),
    )
    await user.type(
      screen.getByPlaceholderText('hola@thiagobarber.co'),
      'ana@barberflow.test',
    )
    await user.click(
      screen.getByRole('button', { name: /Enviar enlace de recuperación/i }),
    )

    expect(await screen.findByText('REVISA TU CORREO')).toBeInTheDocument()
    const [url, opciones] = fetchMock.mock.calls[0] as unknown as [string, RequestInit]
    expect(url).toMatch(/\/api\/v1\/auth\/password-reset$/)
    expect(JSON.parse(opciones.body as string)).toEqual({
      email: 'ana@barberflow.test',
    })
  })

  it('Dado que el servidor falla, Cuando pide recuperar la contraseña, Entonces muestra el error y no dice que se envió', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() => respuesta(500)),
    )
    const user = userEvent.setup()
    render(<LoginForm />)

    await user.click(
      screen.getByRole('button', { name: /¿Olvidaste tu contraseña\?/i }),
    )
    await user.type(
      screen.getByPlaceholderText('hola@thiagobarber.co'),
      'ana@barberflow.test',
    )
    await user.click(
      screen.getByRole('button', { name: /Enviar enlace de recuperación/i }),
    )

    expect(await screen.findByText(/No pudimos enviar el correo/)).toBeInTheDocument()
    expect(screen.queryByText('REVISA TU CORREO')).not.toBeInTheDocument()
  })

  it('Dado el enlace del correo, Cuando elige una contraseña nueva, Entonces la envía con uid y token y vuelve al login con aviso', async () => {
    const fetchMock = vi.fn(() => respuesta(200, { detail: 'ok' }))
    vi.stubGlobal('fetch', fetchMock)
    const user = userEvent.setup()
    render(<LoginForm restablecer={{ uid: 'MQ', token: 'abc-123' }} />)

    await user.type(
      screen.getByPlaceholderText('Mínimo 8 caracteres'),
      'Navaja.Dorada-2027',
    )
    await user.type(
      screen.getByPlaceholderText('Repite la contraseña'),
      'Navaja.Dorada-2027',
    )
    await user.click(screen.getByRole('button', { name: /Cambiar contraseña/i }))

    expect(await screen.findByText(/Contraseña actualizada/)).toBeInTheDocument()
    const [url, opciones] = fetchMock.mock.calls[0] as unknown as [string, RequestInit]
    expect(url).toMatch(/\/api\/v1\/auth\/password-reset\/confirm$/)
    expect(JSON.parse(opciones.body as string)).toEqual({
      uid: 'MQ',
      token: 'abc-123',
      password: 'Navaja.Dorada-2027',
    })
  })

  it('Dado dos contraseñas distintas, Cuando intenta cambiarla, Entonces avisa sin llamar a la API', async () => {
    const fetchMock = vi.fn()
    vi.stubGlobal('fetch', fetchMock)
    const user = userEvent.setup()
    render(<LoginForm restablecer={{ uid: 'MQ', token: 'abc-123' }} />)

    await user.type(
      screen.getByPlaceholderText('Mínimo 8 caracteres'),
      'Navaja.Dorada-2027',
    )
    await user.type(
      screen.getByPlaceholderText('Repite la contraseña'),
      'Otra.Cosa-2027',
    )
    await user.click(screen.getByRole('button', { name: /Cambiar contraseña/i }))

    expect(await screen.findByText('Las contraseñas no coinciden')).toBeInTheDocument()
    expect(fetchMock).not.toHaveBeenCalled()
  })

  it('Dado un enlace vencido, Cuando cambia la contraseña, Entonces muestra el mensaje del servidor', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() =>
        respuesta(400, {
          detail: 'El enlace no es válido o ya venció. Solicita uno nuevo.',
        }),
      ),
    )
    const user = userEvent.setup()
    render(<LoginForm restablecer={{ uid: 'MQ', token: 'viejo' }} />)

    await user.type(
      screen.getByPlaceholderText('Mínimo 8 caracteres'),
      'Navaja.Dorada-2027',
    )
    await user.type(
      screen.getByPlaceholderText('Repite la contraseña'),
      'Navaja.Dorada-2027',
    )
    await user.click(screen.getByRole('button', { name: /Cambiar contraseña/i }))

    expect(
      await screen.findByText(/El enlace no es válido o ya venció/),
    ).toBeInTheDocument()
  })
})
