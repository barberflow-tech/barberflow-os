import { Scissors } from 'lucide-react'
import { useEffect, useState } from 'react'
import { listarServicios, type Servicio } from '@/lib/reservaApi'
import { useReservaWizardStore } from '@/stores/useReservaWizardStore'
import { cn } from '@/lib/utils'
import { tarjeta, tarjetaActiva } from './estilos'
import { formatearPrecio } from './formato'

export function PasoServicio() {
  const [servicios, setServicios] = useState<Servicio[] | null>(null)
  const elegido = useReservaWizardStore((s) => s.servicio)
  const seleccionar = useReservaWizardStore((s) => s.seleccionarServicio)

  useEffect(() => {
    let activo = true
    void listarServicios().then((data) => {
      if (activo) setServicios(data)
    })
    return () => {
      activo = false
    }
  }, [])

  if (!servicios) return <p className="text-sm text-slate-500">Cargando servicios…</p>

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
                'flex size-10 shrink-0 items-center justify-center rounded-xl bg-slate-100 text-slate-500',
                activo && 'bg-[#E5283C] text-white',
              )}
            >
              <Scissors className="size-4" />
            </span>
            <span className="min-w-0 flex-1">
              <span className="block text-sm font-semibold text-[#0B1B3A]">
                {s.nombre}
              </span>
              <span className="block text-xs text-slate-500">{s.duracionMin} min</span>
            </span>
            <span className="text-sm font-bold text-[#0B1B3A]">
              {formatearPrecio(s.precio)}
            </span>
          </button>
        )
      })}
    </div>
  )
}
