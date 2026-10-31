import { create } from 'zustand'

export type Role = 'admin' | 'barbero' | 'cliente'

export interface AuthUser {
  id: number
  email: string
  role: Role
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
  setSession: (session: Session) => void
  clearSession: () => void
  restoreSession: () => Promise<void>
}

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:5000'

// El access token vive solo en memoria; el refresh token va en una cookie HTTP-Only.
export const useAuthStore = create<AuthState>()((set) => ({
  accessToken: null,
  user: null,
  isHydrating: true,

  setSession: ({ accessToken, user }) => set({ accessToken, user, isHydrating: false }),

  clearSession: () => set({ accessToken: null, user: null, isHydrating: false }),

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
