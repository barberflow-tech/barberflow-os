import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it } from 'vitest'
import { useThemeStore } from '@/stores/useThemeStore'
import { ThemeToggle } from './ThemeToggle'

const renderEn = (ruta: string) =>
  render(
    <MemoryRouter initialEntries={[ruta]}>
      <ThemeToggle />
    </MemoryRouter>,
  )

describe('ThemeToggle', () => {
  beforeEach(() => {
    localStorage.clear()
    document.documentElement.classList.remove('dark')
    useThemeStore.setState({ tema: 'light' })
  })

  it('Dado el modo claro, Cuando se pulsa, Entonces activa el modo oscuro y lo recuerda', async () => {
    renderEn('/')
    await userEvent.click(screen.getByRole('button', { name: 'Cambiar a modo oscuro' }))
    expect(document.documentElement).toHaveClass('dark')
    expect(localStorage.getItem('barberflow-tema')).toBe('dark')
    expect(
      screen.getByRole('button', { name: 'Cambiar a modo claro' }),
    ).toBeInTheDocument()
  })

  it('Dado el modo oscuro, Cuando se pulsa, Entonces vuelve al modo claro', async () => {
    useThemeStore.setState({ tema: 'dark' })
    renderEn('/')
    await userEvent.click(screen.getByRole('button', { name: 'Cambiar a modo claro' }))
    expect(document.documentElement).not.toHaveClass('dark')
  })

  it('Dado el login, Cuando se renderiza, Entonces no muestra el botón', () => {
    renderEn('/login')
    expect(screen.queryByRole('button')).not.toBeInTheDocument()
  })
})
