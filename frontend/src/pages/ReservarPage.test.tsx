import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useAuthStore, type AuthUser } from '@/stores/useAuthStore'
import { useReservaWizardStore } from '@/stores/useReservaWizardStore'
import { ReservarPage } from './ReservarPage'

vi.mock('@/lib/reservaApi', async (importOriginal) => {
  const real = await importOriginal<typeof import('@/lib/reservaApi')>()
  return {
    ReservaError: real.ReservaError,
    listarServicios: vi
      .fn()
      .mockResolvedValue([
        { id: 1, nombre: 'Corte clásico', precio: 25000, duracionMin: 45 },
      ]),
    listarBarberos: vi.fn().mockResolvedValue([]),
    listarFranjas: vi.fn().mockResolvedValue([]),
    crearCita: vi.fn(),
  }
})

const usuarios: Record<string, AuthUser> = {
  admin: { id: 2, email: 'admin@barberflow.test', role: 'admin' },
  barbero: { id: 3, email: 'barbero@barberflow.test', role: 'barbero' },
  cliente: { id: 4, email: 'cliente@barberflow.test', role: 'cliente' },
}

describe('ReservarPage según quién la abre', () => {
  beforeEach(() => {
    useReservaWizardStore.getState().reiniciar()
  })

  it.each(['admin', 'barbero', 'cliente', 'visitante'])(
    'Dado un %s, Cuando abre la reserva, Entonces el asistente carga sin quedarse en bucle',
    async (quien) => {
      useAuthStore.setState({
        accessToken: quien === 'visitante' ? null : 'tok',
        user: usuarios[quien] ?? null,
        isHydrating: false,
      })

      render(
        <MemoryRouter initialEntries={['/reservar']}>
          <ReservarPage />
        </MemoryRouter>,
      )

      expect(await screen.findByText(/corte clásico/i)).toBeInTheDocument()
      expect(screen.getByText(/paso 1 de 4/i)).toBeInTheDocument()
    },
    10000,
  )
})
