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
      <p
        role="alert"
        className="mt-10 rounded-[14px] border border-[#B3263B]/30 bg-[#FBEEF0] px-4 py-3 text-sm font-medium text-[#B3263B] dark:border-[#E5283C]/30 dark:bg-[#E5283C]/10 dark:text-[#E5283C]"
      >
        No pudimos cargar los servicios en este momento. Inténtalo de nuevo en unos
        minutos.
      </p>
    )
  }
  if (!servicios) {
    return (
      <p className="mt-10 text-sm text-[#101820]/60 dark:text-[#F7F1E8]/60">
        Cargando servicios…
      </p>
    )
  }
  if (servicios.length === 0) {
    return (
      <p className="mt-10 text-sm text-[#101820]/70 dark:text-[#F7F1E8]/70">
        Pronto publicaremos nuestros servicios.
      </p>
    )
  }

  return (
    <ul className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      {servicios.map((servicio) => (
        <li
          key={servicio.id}
          className="bf-tarjeta group flex flex-col gap-3 border-t-4 border-t-[#B3263B] p-5 dark:border-t-[#E5283C] dark:bg-[#16202B]"
        >
          <span className="grid size-10 place-items-center rounded-lg bg-[#101820] text-[#F7F1E8] transition-colors group-hover:bg-[#B3263B] dark:bg-[#F7F1E8] dark:text-[#101820] dark:group-hover:bg-[#E5283C] dark:group-hover:text-[#101820]">
            <Scissors className="size-5" aria-hidden="true" />
          </span>
          <h3 className="font-[Barlow_Condensed] text-lg font-bold tracking-wide text-[#101820] uppercase dark:text-[#F7F1E8]">
            {servicio.nombre}
          </h3>
          {servicio.descripcion && (
            <p className="flex-1 text-sm text-[#101820]/70 dark:text-[#F7F1E8]/70">
              {servicio.descripcion}
            </p>
          )}
          <p className="text-sm font-semibold text-[#B3263B] dark:text-[#E5283C]">
            {formatearPrecio(servicio.precio)}{' '}
            <span className="font-normal text-[#101820]/55 dark:text-[#F7F1E8]/55">
              · {servicio.duracionMin} min
            </span>
          </p>
        </li>
      ))}
    </ul>
  )
}
