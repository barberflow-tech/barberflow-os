import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import App from './App'

describe('App', () => {
  it('renders the services catalog title', () => {
    render(<App />)
    // Valida el título correcto de la HU-10 que está renderizando la app
    expect(screen.getByText(/Catálogo de Servicios/i)).toBeInTheDocument()
  })
})
