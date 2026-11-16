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

/** Primer mensaje de validación que devuelve DRF ({campo: ["mensaje"]}). */
function primerMensaje(cuerpo: unknown): string | null {
  if (cuerpo && typeof cuerpo === 'object') {
    for (const valor of Object.values(cuerpo)) {
      const mensaje = Array.isArray(valor) ? valor[0] : valor
      if (typeof mensaje === 'string') return mensaje
    }
  }
  return null
}

/**
 * Pide el correo de recuperación (POST /api/v1/auth/password-reset). El backend responde
 * igual exista o no la cuenta, así que un éxito no confirma que el correo esté registrado.
 */
export async function solicitarRecuperacion(email: string): Promise<void> {
  let response: Response
  try {
    response = await fetch(`${API_URL}/api/v1/auth/password-reset`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email }),
    })
  } catch {
    throw new AuthError('No se pudo conectar con el servidor. Inténtalo de nuevo.')
  }

  if (response.status === 429) {
    throw new AuthError(
      'Hiciste demasiadas solicitudes. Inténtalo de nuevo en una hora.',
    )
  }
  if (response.status === 400) {
    throw new AuthError('Ingresa un correo electrónico válido.')
  }
  if (!response.ok) {
    throw new AuthError('No pudimos enviar el correo. Inténtalo de nuevo más tarde.')
  }
}

/** Fija la nueva contraseña con el uid y el token del enlace (POST /auth/password-reset/confirm). */
export async function restablecerContrasena(
  uid: string,
  token: string,
  password: string,
): Promise<void> {
  let response: Response
  try {
    response = await fetch(`${API_URL}/api/v1/auth/password-reset/confirm`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ uid, token, password }),
    })
  } catch {
    throw new AuthError('No se pudo conectar con el servidor. Inténtalo de nuevo.')
  }

  if (response.status === 400) {
    const detalle = primerMensaje(await response.json().catch(() => null))
    throw new AuthError(detalle ?? 'Revisa los datos e inténtalo de nuevo.')
  }
  if (response.status === 429) {
    throw new AuthError('Demasiados intentos. Inténtalo de nuevo más tarde.')
  }
  if (!response.ok) {
    throw new AuthError(
      'No pudimos cambiar tu contraseña. Inténtalo de nuevo más tarde.',
    )
  }
}

/** Crea una cuenta de cliente (POST /api/v1/auth/register). No inicia sesión. */
export async function registrarCuenta(
  fullName: string,
  email: string,
  password: string,
): Promise<void> {
  let response: Response
  try {
    response = await fetch(`${API_URL}/api/v1/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ fullName, email, password }),
    })
  } catch {
    throw new AuthError('No se pudo conectar con el servidor. Inténtalo de nuevo.')
  }

  if (response.status === 400) {
    const detalle = primerMensaje(await response.json().catch(() => null))
    throw new AuthError(detalle ?? 'Revisa los datos e inténtalo de nuevo.')
  }
  if (!response.ok) {
    throw new AuthError('No pudimos crear tu cuenta. Inténtalo de nuevo más tarde.')
  }
}
