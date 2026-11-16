import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { PortafolioPage } from './PortafolioPage'

const foto = {
  id: 7,
  image_url: 'http://storage.test/a.webp',
  original_filename: 'fade.png',
  original_size: 10,
  optimized_size: 5,
  created_at: '2026-11-04T10:00:00Z',
}

function respuesta(cuerpo: unknown, status = 200) {
  return Promise.resolve(new Response(JSON.stringify(cuerpo), { status }))
}

/** Responde por URL: los servicios del barbero van aparte del portafolio. */
function simular(portafolio: () => Promise<Response>) {
  return vi.fn((url: string) =>
    url.includes('/me/services') ? respuesta([]) : portafolio(),
  )
}

describe('PortafolioPage', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('Dado un barbero con fotos, Cuando carga, Entonces muestra su portafolio real', async () => {
    vi.stubGlobal(
      'fetch',
      simular(() => respuesta([{ ...foto, servicio: null, nota: '' }])),
    )
    render(<PortafolioPage />)

    expect(await screen.findByRole('heading', { name: 'fade' })).toBeInTheDocument()
    expect(screen.getByText('1 fotografía')).toBeInTheDocument()
  })

  it('Dado un barbero sin fotos, Cuando carga, Entonces ofrece subir la primera', async () => {
    vi.stubGlobal(
      'fetch',
      simular(() => respuesta([])),
    )
    render(<PortafolioPage />)

    expect(await screen.findByText('Aún no tienes fotografías')).toBeInTheDocument()
  })

  it('Dado un fallo del servidor, Cuando carga, Entonces avisa y permite reintentar', async () => {
    const portafolio = vi
      .fn()
      .mockImplementationOnce(() => respuesta({}, 403))
      .mockImplementationOnce(() => respuesta([{ ...foto, servicio: null, nota: '' }]))
    const fetchMock = simular(portafolio)
    vi.stubGlobal('fetch', fetchMock)
    render(<PortafolioPage />)

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Tu cuenta no está vinculada a un barbero.',
    )
    await userEvent.click(screen.getByRole('button', { name: 'Reintentar' }))
    await waitFor(() =>
      expect(screen.getByRole('heading', { name: 'fade' })).toBeInTheDocument(),
    )
  })
})
