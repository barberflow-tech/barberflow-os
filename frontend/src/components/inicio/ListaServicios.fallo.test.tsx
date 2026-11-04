import { render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { ListaServicios } from './ListaServicios'

// Sin vi.fn: el rechazo ocurre en el código real y el componente debe atraparlo.
describe('ListaServicios con el backend caído', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('Dado un 500, Cuando carga, Entonces muestra un aviso y no servicios inventados', async () => {
    vi.stubGlobal('fetch', () => Promise.resolve({ ok: false, status: 500 }))
    render(<ListaServicios />)
    expect(await screen.findByRole('alert')).toHaveTextContent(/No pudimos cargar/i)
    expect(screen.queryByText('Corte clásico')).not.toBeInTheDocument()
  })
})
