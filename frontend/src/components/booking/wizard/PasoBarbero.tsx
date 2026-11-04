import { useEffect, useState } from 'react'
import { listarBarberos, type Barbero } from '@/lib/reservaApi'
import { useReservaWizardStore } from '@/stores/useReservaWizardStore'
import { cn } from '@/lib/utils'
import { tarjeta, tarjetaActiva } from './estilos'

const iniciales = (nombre: string) => nombre.slice(0, 2).toUpperCase()

export function PasoBarbero() {
  const [barberos, setBarberos] = useState<Barbero[] | null>(null)
  const elegido = useReservaWizardStore((s) => s.barbero)
  const seleccionar = useReservaWizardStore((s) => s.seleccionarBarbero)

  useEffect(() => {
    let activo = true
    void listarBarberos().then((data) => {
      if (activo) setBarberos(data)
    })
    return () => {
      activo = false
    }
  }, [])

  if (!barberos)
    return (
      <p className="text-sm text-slate-500 dark:text-white/55">Cargando barberos…</p>
    )

  return (
    <div className="grid gap-3 sm:grid-cols-3">
      {barberos.map((b) => {
        const activo = elegido?.id === b.id
        return (
          <button
            key={b.id}
            type="button"
            aria-pressed={activo}
            onClick={() => seleccionar(b)}
            className={cn(
              tarjeta,
              'flex flex-col items-center gap-1 px-4 py-6 text-center',
              activo && tarjetaActiva,
            )}
          >
            <span
              aria-hidden="true"
              className="mb-2 flex size-14 items-center justify-center rounded-full bg-[#0B1B3A] dark:bg-[#171c17] text-sm font-bold text-white"
            >
              {iniciales(b.nombre)}
            </span>
            <span className="text-sm font-bold text-[#0B1B3A] dark:text-[#f4f1e9]">
              {b.nombre}
            </span>
            <span className="text-xs text-slate-500 dark:text-white/55">{b.rol}</span>
            <span className="mt-1 text-xs text-slate-500 dark:text-white/55">
              <span className="text-amber-500">★</span>{' '}
              <span className="font-semibold text-amber-600">
                {b.calificacion.toFixed(1)}
              </span>{' '}
              · Disponible
            </span>
          </button>
        )
      })}
    </div>
  )
}
