import { CalendarClock, Clock, Trash2 } from 'lucide-react'
import type { CitaConfirmada } from '@/lib/reservaApi'
import { cn } from '@/lib/utils'
import { botonSecundario, titulo } from '@/components/booking/wizard/estilos'
import { fechaLocal, formatearPrecio } from '@/components/booking/wizard/formato'
import { puedeReprogramar, textoHoras } from './reglas'

const ESTADOS: Record<string, { texto: string; clase: string }> = {
  PENDING: {
    texto: 'Pendiente',
    clase: 'bg-amber-50 text-amber-700 dark:bg-amber-400/10 dark:text-amber-200',
  },
  CONFIRMED: {
    texto: 'Confirmada',
    clase:
      'bg-emerald-50 text-emerald-700 dark:bg-emerald-400/10 dark:text-emerald-300',
  },
}

const iniciales = (nombre: string) => nombre.slice(0, 2).toUpperCase()

/** Límite para reprogramar, en la hora de la barbería: «jue 19 nov, 17:00». */
const limiteLegible = (iso: string) =>
  new Date(iso)
    .toLocaleString('es-CO', {
      weekday: 'short',
      day: 'numeric',
      month: 'short',
      hour: '2-digit',
      minute: '2-digit',
      hourCycle: 'h23',
      timeZone: 'America/Bogota',
    })
    .replace(/\./g, '')

interface Props {
  cita: CitaConfirmada
  /** Instante actual (ms); lo pasa la página para que todas las tarjetas coincidan. */
  ahora: number
  onReprogramar: () => void
  onCancelar: () => void
}

export function TarjetaCita({ cita, ahora, onReprogramar, onCancelar }: Props) {
  const fecha = fechaLocal(cita.inicio.slice(0, 10))
  const hora = cita.inicio.slice(11, 16)
  const estado = ESTADOS[cita.estado] ?? {
    texto: cita.estado,
    clase: 'bg-slate-100 text-slate-600 dark:bg-white/10 dark:text-white/60',
  }
  const reprogramable = puedeReprogramar(cita, ahora)

  return (
    <li className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm dark:border-white/10 dark:bg-[#151915]">
      <div className="flex gap-4 p-4 sm:p-5">
        <div
          aria-hidden="true"
          className="flex w-16 shrink-0 flex-col items-center justify-center rounded-xl bg-[#0B1B3A] py-3 text-white dark:bg-[#d7b36a]/15 dark:text-[#d7b36a]"
        >
          <span className="text-[10px] font-semibold uppercase tracking-wider opacity-70">
            {fecha.toLocaleDateString('es-CO', { weekday: 'short' }).replace('.', '')}
          </span>
          <span className="font-[Barlow_Condensed] text-3xl font-bold leading-none">
            {fecha.getDate()}
          </span>
          <span className="text-[10px] font-semibold uppercase tracking-wider opacity-70">
            {fecha.toLocaleDateString('es-CO', { month: 'short' }).replace('.', '')}
          </span>
        </div>

        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-start justify-between gap-2">
            <h3 className={`${titulo} text-xl leading-tight`}>
              {cita.servicio.nombre}
            </h3>
            <span
              className={cn(
                'rounded-full px-2.5 py-1 text-[11px] font-semibold',
                estado.clase,
              )}
            >
              {estado.texto}
            </span>
          </div>

          <p className="mt-1 text-sm font-medium capitalize text-[#0B1B3A] dark:text-[#f4f1e9]">
            {fecha.toLocaleDateString('es-CO', {
              weekday: 'long',
              day: 'numeric',
              month: 'long',
            })}{' '}
            · {hora}
          </p>

          <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1.5 text-sm text-slate-500 dark:text-white/55">
            <span className="inline-flex items-center gap-2">
              <span
                aria-hidden="true"
                className="flex size-6 items-center justify-center rounded-full bg-[#0B1B3A] text-[10px] font-bold text-white dark:bg-white/10 dark:text-[#f4f1e9]"
              >
                {iniciales(cita.barbero.nombre)}
              </span>
              {cita.barbero.nombre}
            </span>
            <span className="inline-flex items-center gap-1.5">
              <Clock className="size-3.5" aria-hidden="true" />
              {cita.servicio.duracionMin} min
            </span>
            <span className="font-semibold text-[#0B1B3A] dark:text-[#f4f1e9]">
              {formatearPrecio(cita.total)}
            </span>
          </div>
        </div>
      </div>

      <div className="flex flex-col gap-3 border-t border-slate-100 bg-slate-50/60 px-4 py-3 dark:border-white/5 dark:bg-white/[0.02] sm:flex-row sm:items-center sm:justify-between sm:px-5">
        <p
          className={cn(
            'text-xs',
            reprogramable
              ? 'text-slate-500 dark:text-white/50'
              : 'font-medium text-amber-700 dark:text-amber-300',
          )}
        >
          {reprogramable
            ? cita.reprogramarAntes
              ? `Puedes reprogramar hasta el ${limiteLegible(cita.reprogramarAntes)}.`
              : ''
            : `Faltan menos de ${textoHoras(cita.horasAntelacion)}: ya no se puede reprogramar. Si cancelas, quedará como cancelación tardía.`}
        </p>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={onReprogramar}
            disabled={!reprogramable}
            className={`${botonSecundario} h-10 gap-2`}
          >
            <CalendarClock className="size-4" aria-hidden="true" />
            Reprogramar
          </button>
          <button
            type="button"
            onClick={onCancelar}
            className="inline-flex h-10 items-center justify-center gap-2 rounded-xl border border-[#E5283C]/30 bg-white px-4 text-sm font-semibold text-[#E5283C] transition-colors hover:bg-[#FEF2F3] dark:border-red-400/30 dark:bg-transparent dark:text-red-300 dark:hover:bg-red-400/10"
          >
            <Trash2 className="size-4" aria-hidden="true" />
            Cancelar
          </button>
        </div>
      </div>
    </li>
  )
}
