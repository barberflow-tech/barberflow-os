import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import App from './App'

describe('App', () => {
  it('renders the calendar and availability title', () => {
    render(<App />)
    // Evalúa que el título real renderizado en pantalla esté presente
    expect(screen.getByText(/CALENDARIO Y DISPONIBILIDAD/i)).toBeInTheDocument()
  })
})
