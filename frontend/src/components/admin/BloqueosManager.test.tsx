import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { BloqueosManager } from './BloqueosManager'
import { obtenerBloqueosApi } from '@/lib/reservaApi'

vi.mock('@/lib/reservaApi', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/lib/reservaApi')>()
  return {
    ...actual,
    obtenerBloqueosApi: vi.fn(),
    crearBloqueoApi: vi.fn(),
    actualizarBloqueoApi: vi.fn(),
    eliminarBloqueoApi: vi.fn(),
  }
})

describe('BloqueosManager', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('Dado un bloqueo existente en el store, Cuando carga el componente, Entonces lo renderiza en la lista con formato 12h', async () => {
    vi.mocked(obtenerBloqueosApi).mockResolvedValue([
      {
        id: '1',
        barberoId: 1,
        fecha: '2026-12-01',
        horaInicio: '08:00',
        horaFin: '13:00',
        motivo: 'Cita médica',
      },
    ])

    render(<BloqueosManager />)

    expect(await screen.findByText('Cita médica')).toBeInTheDocument()
    expect(screen.getByText('08:00 AM – 01:00 PM')).toBeInTheDocument()
  })

  it('Dado un formulario vacío, Cuando se abre el modal, Entonces el botón de confirmar está deshabilitado', async () => {
    vi.mocked(obtenerBloqueosApi).mockResolvedValue([])
    render(<BloqueosManager />)

    fireEvent.click(await screen.findByText('Crear bloqueo'))

    const botonGuardar = await screen.findByTestId('btn-registrar-bloqueo')
    expect(botonGuardar).toHaveTextContent('Confirmar bloqueo')
    expect(botonGuardar).toBeDisabled()
  })

  it('Dada una hora de inicio seleccionada, Cuando elige la hora de finalización, Entonces deshabilita horas anteriores o iguales y valida rangos incompletos', async () => {
    vi.mocked(obtenerBloqueosApi).mockResolvedValue([])
    render(<BloqueosManager />)

    // 1. Abrir modal
    fireEvent.click(await screen.findByText('Crear bloqueo'))

    // 2. Seleccionar fecha usando el calendario personalizado ("Ir a hoy")
    fireEvent.click(await screen.findByText('Seleccionar fecha'))
    fireEvent.click(screen.getByRole('button', { name: 'Ir a hoy' }))

    // 3. Escribir motivo
    fireEvent.change(screen.getByTestId('input-motivo'), {
      target: { value: 'Mantenimiento' },
    })

    // 4. Seleccionar 03:00 PM en "Hora de inicio" (primer bloque de horarios)
    const botones3PM = screen.getAllByRole('button', { name: '03:00 PM' })
    fireEvent.click(botones3PM[0])

    // En "Hora de finalización" (segundo bloque), las horas <= 03:00 PM quedan deshabilitadas
    const botones10AM = screen.getAllByRole('button', { name: '10:00 AM' })
    const botones4PM = screen.getAllByRole('button', { name: '04:00 PM' })
    expect(botones10AM[1]).toBeDisabled()
    expect(botones3PM[1]).toBeDisabled()
    expect(botones4PM[1]).not.toBeDisabled()

    // 5. Si intenta enviar el formulario sin hora de fin válida, muestra el mensaje de error
    const form = screen.getByTestId('btn-registrar-bloqueo').closest('form')!
    fireEvent.submit(form)

    expect(await screen.findByTestId('error-bloqueo')).toHaveTextContent(
      'Selecciona las horas de inicio y finalización.',
    )
  })
})
