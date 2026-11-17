import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it } from 'vitest'
import { useAuthStore } from '@/stores/useAuthStore'
import { PerfilAdminPage } from './PerfilAdminPage'

function renderPagina() {
  return render(
    <MemoryRouter initialEntries={['/admin/perfil']}>
      <PerfilAdminPage />
    </MemoryRouter>,
  )
}

describe('PerfilAdminPage', () => {
  beforeEach(() => {
    useAuthStore.setState({
      accessToken: 'tok',
      user: {
        id: 2,
        email: 'admin@barberflow.test',
        role: 'admin',
        fullName: 'Ana Admin',
      },
      isHydrating: false,
    })
  })

  it('Dado un admin con sesión, Cuando abre Mi perfil, Entonces ve su nombre, su correo y su rol', () => {
    renderPagina()

    expect(screen.getByRole('heading', { name: /mi perfil/i })).toBeInTheDocument()
    expect(screen.getAllByText('Ana Admin').length).toBeGreaterThan(0)
    expect(screen.getAllByText('admin@barberflow.test').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Administrador').length).toBeGreaterThan(0)
  })

  it('Dado un admin, Cuando abre Mi perfil, Entonces ve el panel decorativo a la derecha con su rol', () => {
    renderPagina()

    const panel = screen.getByTestId('perfil-decoracion')
    expect(panel).toHaveAttribute('aria-hidden', 'true')
    expect(panel).toHaveTextContent(/barberflow/i)
    expect(panel).toHaveTextContent(/administrador/i)
  })

  it('Dado una cuenta sin nombre guardado, Cuando abre Mi perfil, Entonces no muestra un nombre vacío', () => {
    useAuthStore.setState({
      user: { id: 2, email: 'admin@barberflow.test', role: 'admin' },
    })

    renderPagina()

    expect(screen.getAllByText(/sin nombre registrado/i).length).toBeGreaterThan(0)
  })
})
