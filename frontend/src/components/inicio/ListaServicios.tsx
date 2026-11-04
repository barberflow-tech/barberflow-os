import { Scissors } from 'lucide-react'
import { useEffect, useState } from 'react'
import { formatearPrecio } from '@/components/booking/wizard/formato'
import { listarServicios, type Servicio } from '@/lib/reservaApi'

/** Servicios de la portada: salen del catálogo real (GET /api/v1/services). */
export function ListaServicios() {
  const [servicios, setServicios] = useState<Servicio[] | null>(null)
  const [fallo, setFallo] = useState(false)

  useEffect(() => {
    let activo = true
    async function cargar() {
      try {
        const data = await listarServicios()
        if (activo) setServicios(data)
      } catch {
        if (activo) setFallo(true)
      }
    }
    void cargar()
    return () => {
      activo = false
    }
  }, [])

  if (fallo) {
    return (
      <p role="alert" className="mt-10 text-sm text-slate-600 dark:text-white/65">
        No pudimos cargar los servicios en este momento. Inténtalo de nuevo en unos
        minutos.
      </p>
    )
  }
  if (!servicios) {
    return (
      <p className="mt-10 text-sm text-slate-500 dark:text-white/55">
        Cargando servicios…
      </p>
    )
  }
  if (servicios.length === 0) {
    return (
      <p className="mt-10 text-sm text-slate-600 dark:text-white/65">
        Pronto publicaremos nuestros servicios.
      </p>
    )
  }

  return (
    <ul className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      {servicios.map((servicio) => (
        <li
          key={servicio.id}
          className="space-y-3 rounded-xl border bg-white dark:bg-[#151915] p-5 transition-colors hover:border-slate-300 dark:hover:border-white/20"
        >
          <span className="grid size-10 place-items-center rounded-lg bg-[#FEF2F3] dark:bg-[#d7b36a]/10 text-[#E5283C] dark:text-[#d7b36a]">
            <Scissors className="size-5" aria-hidden="true" />
          </span>
          <h3 className="font-semibold">{servicio.nombre}</h3>
          {servicio.descripcion && (
            <p className="text-sm text-slate-600 dark:text-white/65">
              {servicio.descripcion}
            </p>
          )}
          <p className="text-sm font-semibold text-slate-900 dark:text-[#f4f1e9]">
            {formatearPrecio(servicio.precio)}{' '}
            <span className="font-normal text-slate-500 dark:text-white/55">
              · {servicio.duracionMin} min
            </span>
          </p>
        </li>
      ))}
    </ul>
  )
}
