import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it } from 'vitest'
import App from './App'
import { useAuthStore, type Role } from '@/stores/useAuthStore'

function renderEn(ruta: string) {
  return render(
    <MemoryRouter initialEntries={[ruta]}>
      <App />
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
    expect(screen.getByRole('link', { name: /Reservar cita/i })).toHaveAttribute(
      'href',
      '/reservar',
    )
    expect(screen.getByRole('link', { name: /Ingresar/i })).toHaveAttribute(
      'href',
      '/login',
    )
  })

  it('Dado un visitante, Cuando entra a /login, Entonces ve el formulario de ingreso', () => {
    renderEn('/login')
    expect(screen.getByPlaceholderText('hola@thiagobarber.co')).toBeInTheDocument()
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

  it('Dado un barbero con sesión, Cuando entra a /login, Entonces va a la bienvenida', () => {
    iniciarSesionComo('barbero')
    renderEn('/login')
    expect(
      screen.getByRole('heading', { name: 'Bienvenido a BarberFlow' }),
    ).toBeInTheDocument()
  })

  it('Dado una ruta inexistente, Cuando se visita, Entonces vuelve a la portada', () => {
    renderEn('/no-existe')
    expect(screen.getByRole('link', { name: /Reservar cita/i })).toBeInTheDocument()
  })

  it('Dado el modo desarrollo, Cuando entra a /dev/calendario, Entonces ve el calendario', () => {
    renderEn('/dev/calendario')
    expect(screen.getByText(/CALENDARIO Y DISPONIBILIDAD/i)).toBeInTheDocument()
  })
})
