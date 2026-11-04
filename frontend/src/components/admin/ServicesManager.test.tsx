import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import {
  actualizarServicioApi,
  crearServicioApi,
  eliminarServicioApi,
} from '@/lib/catalogoApi'
import { useServicesStore } from '@/stores/useServicesStore'
import { ServicesManager } from './ServicesManager'

vi.mock('@/lib/catalogoApi', () => ({
  crearServicioApi: vi.fn(async (d: object) => ({ id: 99, ...d })),
  actualizarServicioApi: vi.fn(async (id: number, d: object) => ({
    id: Number(id),
    ...d,
  })),
  eliminarServicioApi: vi.fn(async () => undefined),
  listarServiciosApi: vi.fn().mockResolvedValue([
    {
      id: 1,
      name: 'Corte clásico',
      price: 35000,
      duration_minutes: 40,
      description: '',
      is_active: true,
    },
  ]),
}))

const renderizar = (props: React.ComponentProps<typeof ServicesManager> = {}) =>
  render(
    <MemoryRouter>
      <ServicesManager {...props} />
    </MemoryRouter>,
  )

describe('ServicesManager', () => {
  beforeEach(() => {
    useServicesStore.setState({ services: [], isLoading: false, error: null })
  })

  it('Dado el catálogo del backend, Cuando carga, Entonces muestra nombre, duración y precio', async () => {
    renderizar()
    expect(await screen.findByText('Corte clásico')).toBeInTheDocument()
    expect(screen.getByText(/40 min/)).toBeInTheDocument()
    expect(screen.getByText(/35\.000/)).toBeInTheDocument()
  })

  it('Dado una foto del portafolio, Cuando se configura, Entonces crea el servicio y avisa que la foto se usó', async () => {
    const onFotoUsada = vi.fn()
    renderizar({
      fotosPendientes: [
        { id: 'foto-1', url: 'data:image/jpeg;base64,AAAA', titulo: 'Fade' },
      ],
      onFotoUsada,
    })
    await screen.findByText('Corte clásico')

    await userEvent.click(screen.getByRole('button', { name: /Configurar servicio/i }))
    const nombre = screen.getByLabelText('Nombre')
    await userEvent.clear(nombre)
    await userEvent.type(nombre, 'Fade premium')
    await userEvent.clear(screen.getByLabelText(/Precio/))
    await userEvent.type(screen.getByLabelText(/Precio/), '45000')
    await userEvent.click(screen.getByRole('button', { name: 'Crear servicio' }))

    expect(await screen.findByText('Fade premium')).toBeInTheDocument()
    expect(crearServicioApi).toHaveBeenCalledWith(
      expect.objectContaining({ name: 'Fade premium', price: 45000 }),
    )
    expect(onFotoUsada).toHaveBeenCalledWith('foto-1')
  })

  it('Dado un servicio, Cuando se edita el precio, Entonces la tarjeta lo refleja', async () => {
    renderizar()
    await screen.findByText('Corte clásico')

    await userEvent.click(screen.getByRole('button', { name: /Editar/i }))
    await userEvent.clear(screen.getByLabelText(/Precio/))
    await userEvent.type(screen.getByLabelText(/Precio/), '40000')
    await userEvent.click(screen.getByRole('button', { name: 'Guardar cambios' }))

    expect(await screen.findByText(/40\.000/)).toBeInTheDocument()
    expect(actualizarServicioApi).toHaveBeenCalledWith(
      '1',
      expect.objectContaining({ price: 40000 }),
    )
  })

  it('Dado que el backend rechaza el guardado, Cuando se edita, Entonces muestra el error y conserva el modal', async () => {
    vi.mocked(actualizarServicioApi).mockRejectedValueOnce(
      new Error('Solo un administrador puede modificar el catálogo.'),
    )
    renderizar()
    await screen.findByText('Corte clásico')

    await userEvent.click(screen.getByRole('button', { name: /Editar/i }))
    await userEvent.click(screen.getByRole('button', { name: 'Guardar cambios' }))

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Solo un administrador puede modificar el catálogo.',
    )
    expect(screen.getByRole('dialog', { name: 'Editar servicio' })).toBeInTheDocument()
  })

  it('Dado un servicio, Cuando se confirma la eliminación, Entonces desaparece del catálogo', async () => {
    renderizar()
    await screen.findByText('Corte clásico')

    await userEvent.click(
      screen.getByRole('button', { name: 'Eliminar Corte clásico' }),
    )
    await userEvent.click(screen.getByRole('button', { name: 'Eliminar' }))

    expect(screen.queryByText('Corte clásico')).not.toBeInTheDocument()
    expect(eliminarServicioApi).toHaveBeenCalledWith('1')
  })

  it('Dado que falla la eliminación, Cuando se confirma, Entonces el servicio sigue en la lista y se avisa', async () => {
    vi.mocked(eliminarServicioApi).mockRejectedValueOnce(
      new Error('No se pudo conectar con el servidor.'),
    )
    renderizar()
    await screen.findByText('Corte clásico')

    await userEvent.click(
      screen.getByRole('button', { name: 'Eliminar Corte clásico' }),
    )
    await userEvent.click(screen.getByRole('button', { name: 'Eliminar' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('No se pudo conectar')
    expect(screen.getByText('Corte clásico')).toBeInTheDocument()
  })
})
