import { create } from 'zustand'

export type Tema = 'light' | 'dark'

const CLAVE = 'barberflow-tema'

function temaGuardado(): Tema {
  try {
    return localStorage.getItem(CLAVE) === 'dark' ? 'dark' : 'light'
  } catch {
    return 'light'
  }
}

/** Marca <html> con la clase `dark`, que activa las variantes `dark:` de Tailwind. */
function aplicar(tema: Tema) {
  document.documentElement.classList.toggle('dark', tema === 'dark')
}

interface ThemeState {
  tema: Tema
  alternar: () => void
}

export const useThemeStore = create<ThemeState>()((set, get) => ({
  tema: temaGuardado(),
  alternar: () => {
    const siguiente: Tema = get().tema === 'dark' ? 'light' : 'dark'
    try {
      localStorage.setItem(CLAVE, siguiente)
    } catch {
      // Sin almacenamiento disponible: el tema solo dura mientras la pestaña esté abierta.
    }
    aplicar(siguiente)
    set({ tema: siguiente })
  },
}))

// Aplica el tema guardado al cargar la app.
aplicar(useThemeStore.getState().tema)
