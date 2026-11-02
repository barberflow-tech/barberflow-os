// Llamadas de autenticación al backend (SCRUM-30).
// Mismo contrato que `restoreSession` en useAuthStore: el access token viaja en el
// cuerpo ({ access, user }) y el refresh token en una cookie HTTP-Only.
import type { AuthUser } from '@/stores/useAuthStore'

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:5000'

export interface SesionIniciada {
  accessToken: string
  user: AuthUser
}

/** Error con un mensaje apto para mostrar al usuario. */
export class AuthError extends Error {}

export async function iniciarSesion(
  email: string,
  password: string,
): Promise<SesionIniciada> {
  let response: Response
  try {
    response = await fetch(`${API_URL}/api/v1/auth/login`, {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    })
  } catch {
    throw new AuthError('No se pudo conectar con el servidor. Inténtalo de nuevo.')
  }

  if (response.status === 400 || response.status === 401) {
    throw new AuthError('Correo o contraseña incorrectos')
  }
  if (!response.ok) {
    throw new AuthError('No pudimos iniciar sesión. Inténtalo de nuevo más tarde.')
  }

  const { access, user } = (await response.json()) as { access: string; user: AuthUser }
  return { accessToken: access, user }
}
