import { act, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { useAuthStore } from '@/stores/useAuthStore'
import { AvisoSesionCerrada } from './AvisoSesionCerrada'

describe('AvisoSesionCerrada', () => {
  beforeEach(() => {
    useAuthStore.setState({ sesionCerrada: false })
  })
  afterEach(() => {
    vi.useRealTimers()
  })

  it('Dado que nadie ha cerrado sesión, Cuando se carga la app, Entonces no hay aviso', () => {
    render(<AvisoSesionCerrada />)

    expect(screen.queryByRole('status')).not.toBeInTheDocument()
  })

  it('Dado que el usuario cierra sesión, Cuando termina, Entonces ve que se cerró y que vuelva pronto', () => {
    render(<AvisoSesionCerrada />)

    act(() => useAuthStore.setState({ sesionCerrada: true }))

    const aviso = screen.getByRole('status')
    expect(aviso).toHaveTextContent(/tu sesión se ha cerrado exitosamente/i)
    expect(aviso).toHaveTextContent(/vuelve pronto/i)
  })

  it('Dado el aviso visible, Cuando pasan unos segundos, Entonces desaparece solo', () => {
    vi.useFakeTimers()
    render(<AvisoSesionCerrada />)
    act(() => useAuthStore.setState({ sesionCerrada: true }))

    act(() => {
      vi.advanceTimersByTime(6000)
    })

    expect(screen.queryByRole('status')).not.toBeInTheDocument()
    expect(useAuthStore.getState().sesionCerrada).toBe(false)
  })

  it('Dado el aviso visible, Cuando lo cierra con la X, Entonces se oculta', async () => {
    render(<AvisoSesionCerrada />)
    act(() => useAuthStore.setState({ sesionCerrada: true }))

    await userEvent.click(screen.getByRole('button', { name: /cerrar aviso/i }))

    expect(screen.queryByRole('status')).not.toBeInTheDocument()
  })
})
