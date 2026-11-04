import type { Role } from '@/stores/useAuthStore'

/** Pantalla a la que se envía a cada rol justo después de iniciar sesión. */
export function rutaPorRol(role: Role): string {
  switch (role) {
    case 'admin':
      return '/admin'
    case 'cliente':
      return '/reservar'
    case 'barbero':
      return '/barbero/portafolio'
    default:
      return '/bienvenida'
  }
}
