import { create } from 'zustand'

export type Role = 'admin' | 'barbero' | 'cliente'

export interface AuthUser {
  id: number
  email: string
  role: Role
  /** Nombre con el que se registró; puede faltar en cuentas antiguas. */
  fullName?: string
}

interface Session {
  accessToken: string
  user: AuthUser
}

interface AuthState {
  accessToken: string | null
  user: AuthUser | null
  /** true mientras se renueva la sesión al cargar la app; evita el parpadeo de invitado. */
  isHydrating: boolean
  /** true justo después de que el usuario cierra sesión: la app lo avisa y lo apaga. */
  sesionCerrada: boolean
  descartarSesionCerrada: () => void
  setSession: (session: Session) => void
  clearSession: () => void
  /** Cierra la sesión también en el servidor (borra la cookie del refresh token). */
  logout: () => Promise<void>
  restoreSession: () => Promise<void>
}

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:5000'

// El access token vive solo en memoria; el refresh token va en una cookie HTTP-Only.
export const useAuthStore = create<AuthState>()((set) => ({
  accessToken: null,
  user: null,
  isHydrating: true,
  sesionCerrada: false,

  descartarSesionCerrada: () => set({ sesionCerrada: false }),

  setSession: ({ accessToken, user }) => set({ accessToken, user, isHydrating: false }),

  clearSession: () => set({ accessToken: null, user: null, isHydrating: false }),

  logout: async () => {
    // La cookie del refresh es HttpOnly: solo el servidor puede borrarla. Si falla la
    // red, igual se limpia el estado local para no dejar al usuario atrapado.
    try {
      await fetch(`${API_URL}/api/v1/auth/logout`, {
        method: 'POST',
        credentials: 'include',
      })
    } catch {
      // sin conexión: se continúa con el cierre local
    }
    set({ accessToken: null, user: null, isHydrating: false, sesionCerrada: true })
  },

  restoreSession: async () => {
    try {
      const response = await fetch(`${API_URL}/api/v1/auth/refresh`, {
        method: 'POST',
        credentials: 'include',
      })
      if (!response.ok) {
        set({ accessToken: null, user: null, isHydrating: false })
        return
      }
      const { access, user } = (await response.json()) as {
        access: string
        user: AuthUser
      }
      set({ accessToken: access, user, isHydrating: false })
    } catch {
      set({ accessToken: null, user: null, isHydrating: false })
    }
  },
}))
