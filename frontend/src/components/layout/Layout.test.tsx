import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useAuthStore, type Role } from '@/stores/useAuthStore'
import { Footer } from './Footer'
import { Navbar } from './Navbar'

const enlaces = [{ href: '#servicios', etiqueta: 'Servicios' }]

describe('Navbar', () => {
  it('Dado un visitante, Cuando ve la barra, Entonces tiene el logo, los enlaces y los accesos', () => {
    render(
      <MemoryRouter>
        <Navbar enlaces={enlaces} />
      </MemoryRouter>,
    )
    expect(
      screen.getByRole('link', { name: /BarberFlow, ir al inicio/i }),
    ).toHaveAttribute('href', '/')
    expect(screen.getByRole('link', { name: 'Servicios' })).toHaveAttribute(
      'href',
      '#servicios',
    )
    expect(screen.getByRole('link', { name: 'Ingresar' })).toHaveAttribute(
      'href',
      '/login',
    )
  })

  it('Dado un celular, Cuando abre el menú, Entonces aparecen los enlaces móviles y puede cerrarlo', async () => {
    const user = userEvent.setup()
    render(
      <MemoryRouter>
        <Navbar enlaces={enlaces} />
      </MemoryRouter>,
    )
    expect(screen.queryByRole('navigation', { name: 'Principal móvil' })).toBeNull()

    await user.click(screen.getByRole('button', { name: 'Abrir menú' }))
    expect(
      screen.getByRole('navigation', { name: 'Principal móvil' }),
    ).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Cerrar menú' }))
    expect(screen.queryByRole('navigation', { name: 'Principal móvil' })).toBeNull()
  })
})

describe('Navbar · según la sesión', () => {
  const entrar = (role: Role) =>
    useAuthStore.getState().setSession({
      accessToken: 't',
      user: { id: 1, email: `${role}@barberflow.test`, role },
    })

  beforeEach(() => {
    useAuthStore.setState(useAuthStore.getInitialState(), true)
    useAuthStore.getState().clearSession()
  })

  const renderEn = (ruta = '/') =>
    render(
      <MemoryRouter initialEntries={[ruta]}>
        <Navbar />
      </MemoryRouter>,
    )

  it('Dado un cliente con sesión, Cuando ve la barra, Entonces puede cerrar sesión y no ve «Ingresar»', () => {
    entrar('cliente')
    renderEn()

    expect(screen.getByRole('button', { name: 'Cerrar sesión' })).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Ingresar' })).toBeNull()
    expect(screen.queryByRole('link', { name: 'Panel' })).toBeNull()
  })

  it('Dado un admin con sesión, Cuando ve la barra, Entonces tiene el acceso a su panel', () => {
    entrar('admin')
    renderEn()

    expect(screen.getByRole('link', { name: 'Panel' })).toHaveAttribute(
      'href',
      '/admin',
    )
  })

  it('Dado un barbero con sesión, Cuando ve la barra, Entonces tiene el acceso a su portafolio', () => {
    entrar('barbero')
    renderEn()

    expect(screen.getByRole('link', { name: 'Mi portafolio' })).toHaveAttribute(
      'href',
      '/barbero/portafolio',
    )
  })

  it('Dado que ya está en /reservar, Cuando ve la barra, Entonces no repite «Reservar cita»', () => {
    renderEn('/reservar')

    expect(screen.queryByRole('link', { name: 'Reservar cita' })).toBeNull()
  })

  it('Dado un cliente con sesión, Cuando cierra sesión, Entonces la sesión se limpia', async () => {
    entrar('cliente')
    renderEn()

    await userEvent.click(screen.getByRole('button', { name: 'Cerrar sesión' }))

    await vi.waitFor(() => expect(useAuthStore.getState().user).toBeNull())
  })
})

describe('Footer', () => {
  it('Dado cualquier página, Cuando llega al final, Entonces ve la marca, los enlaces y el copyright', () => {
    render(
      <MemoryRouter>
        <Footer />
      </MemoryRouter>,
    )
    expect(
      screen.getByRole('link', { name: /BarberFlow, ir al inicio/i }),
    ).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Reservar cita' })).toHaveAttribute(
      'href',
      '/reservar',
    )
    expect(screen.getByText(/© 2026 BarberFlow Technologies/)).toBeInTheDocument()
  })
})
