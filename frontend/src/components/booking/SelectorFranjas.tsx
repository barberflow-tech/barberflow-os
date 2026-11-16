import { useFranjas } from '@/hooks/useFranjas'
import { cn } from '@/lib/utils'

interface Props {
  barberoId: number
  /** 'YYYY-MM-DD' */
  fecha: string
  duracionMin?: number
  /** Hora elegida ('HH:MM') o `null`. */
  hora: string | null
  onElegir: (hora: string) => void
  /** Muestra solo las libres (Mis citas); por defecto también las ocupadas, deshabilitadas. */
  ocultarOcupadas?: boolean
  className?: string
}

const mensaje = 'text-sm text-slate-500 dark:text-white/55'

/**
 * Franjas de un barbero para un día. Lo usan el asistente de reserva y la
 * reprogramación de Mis citas, y se actualiza sola cuando Realtime avisa que
 * una franja se liberó u ocupó.
 */
export function SelectorFranjas({
  barberoId,
  fecha,
  duracionMin,
  hora,
  onElegir,
  ocultarOcupadas = false,
  className = 'grid grid-cols-2 gap-2 sm:grid-cols-3',
}: Props) {
  const { franjas, error } = useFranjas(barberoId, fecha, duracionMin)

  if (!franjas) return <p className={mensaje}>Cargando horarios…</p>
  if (error) {
    return (
      <p
        role="alert"
        className="rounded-xl bg-[#FEF2F3] p-3 text-sm text-[#E5283C] dark:bg-[#d7b36a]/10 dark:text-[#d7b36a]"
      >
        {error}
      </p>
    )
  }

  const visibles = ocultarOcupadas ? franjas.filter((f) => f.disponible) : franjas
  if (visibles.length === 0) {
    return (
      <p className={mensaje}>
        No hay horarios disponibles este día. Prueba con otra fecha u otro barbero.
      </p>
    )
  }

  return (
    <div className={className}>
      {visibles.map((f) => (
        <button
          key={f.hora}
          type="button"
          aria-label={`Hora ${f.hora}${f.disponible ? '' : ' (ocupada)'}`}
          aria-pressed={hora === f.hora}
          disabled={!f.disponible}
          onClick={() => onElegir(f.hora)}
          className={cn(
            'h-11 rounded-xl border border-slate-200 bg-white text-sm font-medium text-[#0B1B3A] transition-colors hover:border-slate-300 dark:border-white/10 dark:bg-[#151915] dark:text-[#f4f1e9] dark:hover:border-white/20',
            hora === f.hora &&
              'border-[#E5283C] bg-[#FEF2F3] text-[#E5283C] hover:border-[#E5283C] dark:border-[#d7b36a] dark:bg-[#d7b36a]/10 dark:text-[#d7b36a] dark:hover:border-[#d7b36a]',
            !f.disponible &&
              'cursor-not-allowed border-transparent bg-slate-50 text-slate-300 hover:border-transparent dark:bg-white/5 dark:text-white/30',
          )}
        >
          {f.hora}
        </button>
      ))}
    </div>
  )
}
