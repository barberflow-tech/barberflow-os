import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
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
