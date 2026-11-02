// Reglas de validación de imágenes del portafolio (SCRUM-34, HU-07).

export const MAX_BYTES = 5 * 1024 * 1024
export const TIPOS_PERMITIDOS = ['image/png', 'image/jpeg', 'image/webp']

/** Devuelve el motivo del rechazo, o `null` si la imagen es válida. */
export function validarImagen(archivo: File): string | null {
  if (!TIPOS_PERMITIDOS.includes(archivo.type)) {
    return 'Formato no permitido. Usa PNG, JPG o WEBP.'
  }
  if (archivo.size > MAX_BYTES) {
    return 'Supera el tamaño máximo de 5 MB.'
  }
  return null
}

export function formatearTamano(bytes: number): string {
  return bytes >= 1024 * 1024
    ? `${(bytes / (1024 * 1024)).toFixed(1)} MB`
    : `${Math.max(1, Math.round(bytes / 1024))} KB`
}
