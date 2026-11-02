import { render, screen } from '@testing-library/react'
import App from './App'

describe('App', () => {
  it('renders the login title and welcome message', () => {
    render(<App />)
    expect(screen.getByText(/BIENVENIDO DE NUEVO/i)).toBeInTheDocument()
  })
})
