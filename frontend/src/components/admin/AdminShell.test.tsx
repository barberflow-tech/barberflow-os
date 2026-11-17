import { render, screen, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it } from 'vitest'
import { useAuthStore } from '@/stores/useAuthStore'
import { AdminShell } from './AdminShell'

function renderShell() {
  return render(
    <MemoryRouter initialEntries={['/admin']}>
      <AdminShell>
        <p>contenido</p>
      </AdminShell>
    </MemoryRouter>,
  )
}

describe('AdminShell: menú del administrador', () => {
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

  it('Dado un admin, Cuando ve el menú, Entonces no aparece «Servicios» (ya está en el panel)', () => {
    renderShell()

    const menu = screen.getByRole('navigation', { name: /secciones del panel/i })
    expect(within(menu).queryByRole('link', { name: 'Servicios' })).toBeNull()
  })

  it('Dado un admin, Cuando ve el menú, Entonces tiene Panel, Horarios, Usuarios y Mi perfil', () => {
    renderShell()

    const menu = screen.getByRole('navigation', { name: /secciones del panel/i })
    const etiquetas = within(menu)
      .getAllByRole('link')
      .map((a) => a.textContent)
    expect(etiquetas).toEqual(['Panel', 'Horarios', 'Usuarios', 'Mi perfil'])
    expect(within(menu).getByRole('link', { name: 'Mi perfil' })).toHaveAttribute(
      'href',
      '/admin/perfil',
    )
  })
})
