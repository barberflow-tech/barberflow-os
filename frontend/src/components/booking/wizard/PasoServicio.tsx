import { Scissors } from 'lucide-react'
import { useEffect, useState } from 'react'
import { listarServicios, type Servicio } from '@/lib/reservaApi'
import { useReservaWizardStore } from '@/stores/useReservaWizardStore'
import { cn } from '@/lib/utils'
import { tarjeta, tarjetaActiva } from './estilos'
import { formatearPrecio } from './formato'

export function PasoServicio() {
  const [servicios, setServicios] = useState<Servicio[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const elegido = useReservaWizardStore((s) => s.servicio)
  const seleccionar = useReservaWizardStore((s) => s.seleccionarServicio)

  useEffect(() => {
    let activo = true
    listarServicios()
      .then((data) => {
        if (activo) setServicios(data)
      })
      .catch((e: unknown) => {
        if (activo) {
          setError(
            e instanceof Error ? e.message : 'No se pudieron cargar los servicios.',
          )
        }
      })
    return () => {
      activo = false
    }
  }, [])

  if (error) {
    return (
      <p role="alert" className="text-sm text-[#B3263B] dark:text-[#E5283C]">
        {error}
      </p>
    )
  }
  if (!servicios)
    return (
      <p className="text-sm text-[#101820]/60 dark:text-[#F7F1E8]/60">
        Cargando servicios…
      </p>
    )

  return (
    <div className="grid gap-3 sm:grid-cols-2">
      {servicios.map((s) => {
        const activo = elegido?.id === s.id
        return (
          <button
            key={s.id}
            type="button"
            aria-pressed={activo}
            onClick={() => seleccionar(s)}
            className={cn(
              tarjeta,
              'flex items-center gap-3 p-3 sm:p-4',
              activo && tarjetaActiva,
            )}
          >
            <span
              aria-hidden="true"
              className={cn(
                'flex size-10 shrink-0 items-center justify-center rounded-xl bg-[#101820]/8 text-[#101820]/60 transition-colors dark:bg-[#F7F1E8]/10 dark:text-[#F7F1E8]/60',
                activo &&
                  'bg-[#B3263B] text-[#F7F1E8] dark:bg-[#E5283C] dark:text-[#101820]',
              )}
            >
              <Scissors className="size-4" />
            </span>
            <span className="min-w-0 flex-1">
              <span className="block text-sm font-semibold text-[#101820] dark:text-[#F7F1E8]">
                {s.nombre}
              </span>
              <span className="block text-xs text-[#101820]/55 dark:text-[#F7F1E8]/55">
                {s.duracionMin} min
              </span>
            </span>
            <span className="text-sm font-bold text-[#B3263B] dark:text-[#E5283C]">
              {formatearPrecio(s.precio)}
            </span>
          </button>
        )
      })}
    </div>
  )
}
