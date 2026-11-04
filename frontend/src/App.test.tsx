import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, useLocation } from 'react-router-dom'
import { beforeEach, describe, expect, it } from 'vitest'
import App from './App'
import { useAuthStore, type Role } from '@/stores/useAuthStore'

function RutaActual() {
  return <span data-testid="ruta">{useLocation().pathname}</span>
}

function renderEn(ruta: string) {
  return render(
    <MemoryRouter initialEntries={[ruta]}>
      <App />
      <RutaActual />
    </MemoryRouter>,
  )
}

function iniciarSesionComo(role: Role) {
  useAuthStore.getState().setSession({
    accessToken: 'token',
    user: { id: 1, email: `${role}@barberflow.test`, role },
  })
}

describe('App · rutas', () => {
  beforeEach(() => {
    useAuthStore.setState(useAuthStore.getInitialState(), true)
    useAuthStore.getState().clearSession()
  })

  it('Dado un visitante, Cuando entra a la portada, Entonces ve los accesos a reservar e ingresar', () => {
    renderEn('/')
    const reservar = screen.getAllByRole('link', { name: /Reservar cita/i })
    const ingresar = screen.getAllByRole('link', { name: /^Ingresar$/i })
    expect(reservar.length).toBeGreaterThan(0)
    expect(ingresar.length).toBeGreaterThan(0)
    reservar.forEach((enlace) => expect(enlace).toHaveAttribute('href', '/reservar'))
    ingresar.forEach((enlace) => expect(enlace).toHaveAttribute('href', '/login'))
  })

  it('Dado un visitante, Cuando entra a /login, Entonces ve el formulario de ingreso', () => {
    renderEn('/login')
    expect(screen.getByPlaceholderText('hola@thiagobarber.co')).toBeInTheDocument()
  })

  it('Dado un visitante, Cuando entra a /login, Entonces ve la barra, el pie y el botón de tema', () => {
    renderEn('/login')
    // El logo aparece en la barra y en el pie.
    expect(
      screen.getAllByRole('link', { name: /BarberFlow, ir al inicio/i }),
    ).toHaveLength(2)
    expect(screen.getByText(/© 2026 BarberFlow Technologies/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Cambiar a modo/ })).toBeInTheDocument()
  })

  it('Dado un visitante, Cuando entra a /registro, Entonces abre la pestaña de registro', () => {
    renderEn('/registro')
    expect(screen.getByPlaceholderText('Ej. Thiago Angulo')).toBeInTheDocument()
  })

  it('Dado el login, Cuando pulsa «Registrarme» y vuelve a «Iniciar sesión», Entonces la URL sigue la pestaña', async () => {
    const user = userEvent.setup()
    renderEn('/login')

    await user.click(screen.getByRole('button', { name: 'Registrarme' }))
    expect(screen.getByTestId('ruta')).toHaveTextContent('/registro')

    await user.click(screen.getByRole('button', { name: 'Iniciar sesión' }))
    expect(screen.getByTestId('ruta')).toHaveTextContent('/login')
  })

  it('Dado un visitante, Cuando entra a /reservar, Entonces ve el asistente de reserva', () => {
    renderEn('/reservar')
    expect(screen.getByText('Nuevo agendamiento')).toBeInTheDocument()
  })

  it('Dado un visitante sin sesión, Cuando entra a /admin, Entonces va al login', () => {
    renderEn('/admin')
    expect(screen.getByPlaceholderText('hola@thiagobarber.co')).toBeInTheDocument()
  })

  it('Dado un cliente con sesión, Cuando entra a /admin, Entonces ve "No autorizado"', () => {
    iniciarSesionComo('cliente')
    renderEn('/admin')
    expect(screen.getByRole('heading', { name: 'No autorizado' })).toBeInTheDocument()
  })

  it('Dado un admin con sesión, Cuando entra a /admin, Entonces ve el panel', () => {
    iniciarSesionComo('admin')
    renderEn('/admin')
    expect(
      screen.getByRole('heading', { name: 'Panel de administración' }),
    ).toBeInTheDocument()
  })

  it('Dado un admin con sesión, Cuando entra a /admin/servicios, Entonces ve el catálogo de servicios', () => {
    iniciarSesionComo('admin')
    renderEn('/admin/servicios')
    expect(screen.getByText(/Catálogo de Servicios/i)).toBeInTheDocument()
  })

  it('Dado un cliente con sesión, Cuando entra a /admin/servicios, Entonces ve "No autorizado"', () => {
    iniciarSesionComo('cliente')
    renderEn('/admin/servicios')
    expect(screen.getByRole('heading', { name: 'No autorizado' })).toBeInTheDocument()
  })

  it('Dado un admin con sesión, Cuando entra a /login, Entonces va al panel', () => {
    iniciarSesionComo('admin')
    renderEn('/login')
    expect(
      screen.getByRole('heading', { name: 'Panel de administración' }),
    ).toBeInTheDocument()
  })

  it('Dado un cliente con sesión, Cuando entra a /login, Entonces va a /reservar', () => {
    iniciarSesionComo('cliente')
    renderEn('/login')
    expect(screen.getByText('Nuevo agendamiento')).toBeInTheDocument()
  })

  it('Dado un barbero con sesión, Cuando entra a /login, Entonces va a su portafolio', () => {
    iniciarSesionComo('barbero')
    renderEn('/login')
    expect(
      screen.getByRole('heading', { level: 1, name: /El arte está en/i }),
    ).toBeInTheDocument()
  })

  it('Dado una ruta inexistente, Cuando se visita, Entonces vuelve a la portada', () => {
    renderEn('/no-existe')
    expect(
      screen.getByRole('heading', { level: 1, name: /Tu barbería, bajo control/i }),
    ).toBeInTheDocument()
  })

  it('Dado el modo desarrollo, Cuando entra a /dev/calendario, Entonces ve el calendario', () => {
    renderEn('/dev/calendario')
    expect(screen.getByText(/CALENDARIO Y DISPONIBILIDAD/i)).toBeInTheDocument()
  })
})
