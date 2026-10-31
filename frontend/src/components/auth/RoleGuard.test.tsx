import { act, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { useAuthStore } from '@/stores/useAuthStore'
import { RoleGuard } from './RoleGuard'

function renderEnRuta(ruta: string) {
  return render(
    <MemoryRouter initialEntries={[ruta]}>
      <Routes>
        <Route path="/login" element={<p>Vista de invitado</p>} />
        <Route path="/no-autorizado" element={<p>Sin permiso</p>} />
        <Route element={<RoleGuard allowedRoles={['admin']} />}>
          <Route path="/admin" element={<p>Panel de admin</p>} />
        </Route>
        <Route element={<RoleGuard allowedRoles={['admin', 'barbero']} />}>
          <Route path="/agenda" element={<p>Agenda</p>} />
        </Route>
      </Routes>
    </MemoryRouter>,
  )
}

function iniciarSesionComo(role: 'admin' | 'barbero' | 'cliente') {
  useAuthStore.setState({
    accessToken: 'token',
    user: { id: 1, email: 'x@barberflow.test', role },
    isHydrating: false,
  })
}

describe('RoleGuard', () => {
  beforeEach(() => {
    useAuthStore.setState(useAuthStore.getInitialState(), true)
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('Dado que la sesión se está renovando, Cuando se entra a una ruta privada, Entonces muestra carga y no la vista de invitado', () => {
    renderEnRuta('/admin')

    expect(screen.getByRole('status')).toBeInTheDocument()
    expect(screen.queryByText('Vista de invitado')).not.toBeInTheDocument()
    expect(screen.queryByText('Panel de admin')).not.toBeInTheDocument()
  })

  it('Dado un invitado, Cuando entra a una ruta privada, Entonces va al login', () => {
    useAuthStore.setState({ isHydrating: false })

    renderEnRuta('/admin')

    expect(screen.getByText('Vista de invitado')).toBeInTheDocument()
  })

  it('Dado un Admin, Cuando entra a la ruta de Admin, Entonces ve el panel', () => {
    iniciarSesionComo('admin')

    renderEnRuta('/admin')

    expect(screen.getByText('Panel de admin')).toBeInTheDocument()
  })

  it('Dado un Barbero, Cuando entra a una ruta solo de Admin, Entonces es enviado a no autorizado', () => {
    iniciarSesionComo('barbero')

    renderEnRuta('/admin')

    expect(screen.getByText('Sin permiso')).toBeInTheDocument()
    expect(screen.queryByText('Panel de admin')).not.toBeInTheDocument()
  })

  it('Dado un Cliente, Cuando entra a una ruta de Admin o Barbero, Entonces es enviado a no autorizado', () => {
    iniciarSesionComo('cliente')

    renderEnRuta('/agenda')

    expect(screen.getByText('Sin permiso')).toBeInTheDocument()
  })

  it('Dado un Barbero, Cuando entra a una ruta permitida para su rol, Entonces ve el contenido', () => {
    iniciarSesionComo('barbero')

    renderEnRuta('/agenda')

    expect(screen.getByText('Agenda')).toBeInTheDocument()
  })

  it('Dado un usuario autenticado, Cuando recarga la página (F5), Entonces la sesión se mantiene y la UI no parpadea con vista de invitado', async () => {
    let resolverRefresh: (r: Response) => void = () => {}
    vi.stubGlobal(
      'fetch',
      vi.fn(
        () =>
          new Promise<Response>((resolve) => {
            resolverRefresh = resolve
          }),
      ),
    )

    renderEnRuta('/admin')
    let restauracion: Promise<void> = Promise.resolve()
    act(() => {
      restauracion = useAuthStore.getState().restoreSession()
    })

    expect(screen.queryByText('Vista de invitado')).not.toBeInTheDocument()

    resolverRefresh(
      new Response(
        JSON.stringify({
          access: 'nuevo',
          user: { id: 1, email: 'a@barberflow.test', role: 'admin' },
        }),
        { status: 200 },
      ),
    )
    await act(async () => {
      await restauracion
    })

    await waitFor(() => expect(screen.getByText('Panel de admin')).toBeInTheDocument())
    expect(screen.queryByText('Vista de invitado')).not.toBeInTheDocument()
  })
})
