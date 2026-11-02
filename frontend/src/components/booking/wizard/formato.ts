const pesos = new Intl.NumberFormat('es-CO', {
  style: 'currency',
  currency: 'COP',
  maximumFractionDigits: 0,
})

export const formatearPrecio = (valor: number) => pesos.format(valor)

/** Convierte 'YYYY-MM-DD' en fecha local (evita el desfase de zona de `new Date(str)`). */
export function fechaLocal(fecha: string): Date {
  const [a, m, d] = fecha.split('-').map(Number)
  return new Date(a, m - 1, d)
}

/** Fecha local como 'YYYY-MM-DD'. */
export function aIso(d: Date): string {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

/** 'domingo, 11 de octubre' */
export const fechaLarga = (fecha: string) =>
  fechaLocal(fecha).toLocaleDateString('es-CO', {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
  })

/** '11 de octubre' */
export const diaMes = (fecha: string) =>
  fechaLocal(fecha).toLocaleDateString('es-CO', { day: 'numeric', month: 'long' })

const ZONA = '-05:00' // Popayán, Colombia

/** Une fecha y hora locales en un ISO 8601 con zona (campo start_at del API). */
export const construirInicio = (fecha: string, hora: string) =>
  `${fecha}T${hora}:00${ZONA}`
