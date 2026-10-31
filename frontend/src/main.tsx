import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import './index.css'
import App from './App.tsx'
import { useAuthStore } from '@/stores/useAuthStore'

// Renueva la sesión con la cookie de refresco antes de decidir qué vista mostrar.
void useAuthStore.getState().restoreSession()

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </StrictMode>,
)
