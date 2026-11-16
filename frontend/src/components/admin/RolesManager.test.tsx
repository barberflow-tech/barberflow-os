import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { cambiarRolApi, listarUsuariosApi, UsuariosError } from '@/lib/usuariosApi'
import { useAuthStore } from '@/stores/useAuthStore'
import { RolesManager } from './RolesManager'

vi.mock('@/lib/usuariosApi', async (importOriginal) => {
  const original = await importOriginal<typeof import('@/lib/usuariosApi')>()
  return {
    ...original,
    listarUsuariosApi: vi.fn(),
    cambiarRolApi: vi.fn(),
  }
})

const admin = {
  id: 1,
  email: 'dueno@norte.com',
  full_name: 'Dueño Norte',
  role: 'admin' as const,
  en_barberia: true,
}
const ana = {
  id: 2,
  email: 'ana@norte.com',
  full_name: 'Ana',
  role: 'cliente' as const,
  en_barberia: true,
}

const renderizar = () =>
  render(
    <MemoryRouter>
      <RolesManager />
    </MemoryRouter>,
  )

const fila = (email: string) => screen.getByRole('row', { name: new RegExp(email) })

describe('RolesManager', () => {
  beforeEach(() => {
    vi.mocked(listarUsuariosApi).mockReset().mockResolvedValue([admin, ana])
    vi.mocked(cambiarRolApi).mockReset()
    useAuthStore.setState({
      user: { id: 1, email: 'dueno@norte.com', role: 'admin' },
      accessToken: 'token',
    })
  })

  it('Dado un administrador, Cuando abre la pantalla, Entonces ve los usuarios de su barbería con su rol', async () => {
    renderizar()

    expect(await screen.findByText('ana@norte.com')).toBeInTheDocument()
    expect(within(fila('ana@norte.com')).getByRole('combobox')).toHaveValue('cliente')
    expect(within(fila('dueno@norte.com')).getByRole('combobox')).toHaveValue('admin')
    expect(listarUsuariosApi).toHaveBeenCalledWith()
  })

  it('Dado un administrador, Cuando cambia el rol de un usuario, Entonces se guarda y la fila muestra el rol nuevo', async () => {
    vi.mocked(cambiarRolApi).mockResolvedValue({ ...ana, role: 'barbero' })
    renderizar()
    await screen.findByText('ana@norte.com')

    await userEvent.selectOptions(
      within(fila('ana@norte.com')).getByRole('combobox'),
      'barbero',
    )

    expect(cambiarRolApi).toHaveBeenCalledWith(2, 'barbero')
    expect(await screen.findByRole('status')).toHaveTextContent(
      /ana@norte.com ahora es Barbero/,
    )
    expect(within(fila('ana@norte.com')).getByRole('combobox')).toHaveValue('barbero')
  })

  it('Dado el propio administrador, Cuando ve su fila, Entonces no puede cambiar su rol', async () => {
    renderizar()
    await screen.findByText('ana@norte.com')

    expect(within(fila('dueno@norte.com')).getByRole('combobox')).toBeDisabled()
    expect(within(fila('dueno@norte.com')).getByText(/Tú/)).toBeInTheDocument()
  })

  it('Dado un cambio que el backend rechaza, Cuando falla, Entonces muestra el error y conserva el rol anterior', async () => {
    vi.mocked(cambiarRolApi).mockRejectedValue(
      new UsuariosError('Solo un administrador puede cambiar roles.'),
    )
    renderizar()
    await screen.findByText('ana@norte.com')

    await userEvent.selectOptions(
      within(fila('ana@norte.com')).getByRole('combobox'),
      'admin',
    )

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Solo un administrador puede cambiar roles.',
    )
    expect(within(fila('ana@norte.com')).getByRole('combobox')).toHaveValue('cliente')
  })

  it('Dado un cliente sin barbería, Cuando el admin lo busca por correo, Entonces aparece y puede ascenderlo', async () => {
    const libre = {
      id: 3,
      email: 'libre@correo.com',
      full_name: '',
      role: 'cliente' as const,
      en_barberia: false,
    }
    vi.mocked(cambiarRolApi).mockResolvedValue({
      ...libre,
      role: 'barbero',
      en_barberia: true,
    })
    renderizar()
    await screen.findByText('ana@norte.com')
    vi.mocked(listarUsuariosApi).mockResolvedValueOnce([libre])

    await userEvent.type(screen.getByLabelText(/Buscar por correo/), 'libre@correo.com')
    await userEvent.click(screen.getByRole('button', { name: 'Buscar' }))

    expect(listarUsuariosApi).toHaveBeenLastCalledWith('libre@correo.com')
    expect(await screen.findByText('libre@correo.com')).toBeInTheDocument()
    expect(
      within(fila('libre@correo.com')).getByText(/Sin barbería/),
    ).toBeInTheDocument()

    await userEvent.selectOptions(
      within(fila('libre@correo.com')).getByRole('combobox'),
      'barbero',
    )

    expect(cambiarRolApi).toHaveBeenCalledWith(3, 'barbero')
    expect(
      await within(fila('libre@correo.com')).findByText(/Tu barbería/),
    ).toBeInTheDocument()
  })

  it('Dado una búsqueda sin resultados, Cuando termina, Entonces lo explica', async () => {
    renderizar()
    await screen.findByText('ana@norte.com')
    vi.mocked(listarUsuariosApi).mockResolvedValueOnce([])

    await userEvent.type(screen.getByLabelText(/Buscar por correo/), 'nadie@correo.com')
    await userEvent.click(screen.getByRole('button', { name: 'Buscar' }))

    expect(
      await screen.findByText(/No hay ningún usuario con ese correo/),
    ).toBeInTheDocument()
  })
})
