import { useEffect, useState } from 'react'
import { listarBarberos, type Barbero } from '@/lib/reservaApi'
import { useReservaWizardStore } from '@/stores/useReservaWizardStore'
import { cn } from '@/lib/utils'
import { tarjeta, tarjetaActiva } from './estilos'
import { TrabajosBarbero } from './TrabajosBarbero'

const iniciales = (nombre: string) => nombre.slice(0, 2).toUpperCase()

export function PasoBarbero() {
  // La lista se guarda con el servicio que la originó: al cambiar de servicio
  // se vuelve a mostrar «Cargando» sin llamar a setState dentro del efecto.
  const [resultado, setResultado] = useState<{
    servicioId: number | undefined
    barberos: Barbero[]
  } | null>(null)
  const elegido = useReservaWizardStore((s) => s.barbero)
  const servicio = useReservaWizardStore((s) => s.servicio)
  const seleccionar = useReservaWizardStore((s) => s.seleccionarBarbero)

  const servicioId = servicio?.id

  useEffect(() => {
    let activo = true
    listarBarberos(servicioId)
      .then((barberos) => {
        if (activo) setResultado({ servicioId, barberos })
      })
      .catch(() => {
        if (activo) setResultado({ servicioId, barberos: [] })
      })
    return () => {
      activo = false
    }
  }, [servicioId])

  const barberos =
    resultado && resultado.servicioId === servicioId ? resultado.barberos : null

  if (!barberos)
    return (
      <p className="text-sm text-slate-500 dark:text-white/55">Cargando barberos…</p>
    )

  if (barberos.length === 0)
    return (
      <p role="status" className="text-sm text-slate-500 dark:text-white/55">
        Por ahora ningún barbero realiza este servicio. Elige otro servicio.
      </p>
    )

  return (
    <div className="space-y-6">
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
                {b.calificacion > 0 && (
                  <>
                    <span className="text-amber-500">★</span>{' '}
                    <span className="font-semibold text-amber-600">
                      {b.calificacion.toFixed(1)}
                    </span>{' '}
                    ·{' '}
                  </>
                )}
                Disponible
              </span>
            </button>
          )
        })}
      </div>
      {elegido && <TrabajosBarbero barbero={elegido} servicio={servicio} />}
    </div>
  )
}
