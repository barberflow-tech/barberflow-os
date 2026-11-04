import { render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('@/lib/reservaApi', () => ({ listarServicios: vi.fn() }))

import { listarServicios } from '@/lib/reservaApi'
import { ListaServicios } from './ListaServicios'

describe('ListaServicios', () => {
  beforeEach(() => vi.mocked(listarServicios).mockReset())

  it('Dado el catálogo del backend, Cuando carga, Entonces muestra nombre, descripción, precio y duración', async () => {
    vi.mocked(listarServicios).mockResolvedValue([
      {
        id: 1,
        nombre: 'Corte clásico',
        precio: 35000,
        duracionMin: 40,
        descripcion: 'Acabado limpio.',
      },
    ])
    render(<ListaServicios />)
    expect(await screen.findByText('Corte clásico')).toBeInTheDocument()
    expect(screen.getByText('Acabado limpio.')).toBeInTheDocument()
    expect(screen.getByText(/35\.000/)).toBeInTheDocument()
    expect(screen.getByText(/40 min/)).toBeInTheDocument()
  })

  it('Dado un catálogo vacío, Cuando carga, Entonces avisa que pronto habrá servicios', async () => {
    vi.mocked(listarServicios).mockResolvedValue([])
    render(<ListaServicios />)
    expect(await screen.findByText(/Pronto publicaremos/i)).toBeInTheDocument()
  })
})
