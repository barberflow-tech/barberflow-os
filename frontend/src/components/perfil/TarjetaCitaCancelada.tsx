import { Clock } from 'lucide-react'
import type { CitaHistorial } from '@/lib/reservaApi'
import { cn } from '@/lib/utils'
import { titulo } from '@/components/booking/wizard/estilos'
import { fechaLocal, formatearPrecio } from '@/components/booking/wizard/formato'

const MOTIVOS = {
  cancelled: {
    etiqueta: 'Cancelada por ti',
    clase: 'bg-red-50 text-red-700 dark:bg-red-400/10 dark:text-red-300',
  },
  expired: {
    etiqueta: 'Vencida',
    clase: 'bg-slate-100 text-slate-600 dark:bg-white/10 dark:text-white/60',
  },
} as const

const cuando = (iso: string) =>
  new Date(iso).toLocaleString('es-CO', {
    day: 'numeric',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
    hourCycle: 'h23',
    timeZone: 'America/Bogota',
  })

export function TarjetaCitaCancelada({ cita }: { cita: CitaHistorial }) {
  const fecha = fechaLocal(cita.inicio.slice(0, 10))
  const hora = cita.inicio.slice(11, 16)
  const motivo = MOTIVOS[cita.motivo]

  return (
    <li className="overflow-hidden rounded-2xl border border-slate-200 bg-white p-4 opacity-90 shadow-sm sm:p-5 dark:border-white/10 dark:bg-[#151915]">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <h3 className={`${titulo} text-xl leading-tight`}>{cita.servicio.nombre}</h3>
        <span
          className={cn(
            'rounded-full px-2.5 py-1 text-[11px] font-semibold',
            motivo.clase,
          )}
        >
          {motivo.etiqueta}
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
        <span>{cita.barbero.nombre}</span>
        <span className="inline-flex items-center gap-1.5">
          <Clock className="size-3.5" aria-hidden="true" />
          {cita.servicio.duracionMin} min
        </span>
        <span className="font-semibold text-[#0B1B3A] dark:text-[#f4f1e9]">
          {formatearPrecio(cita.total)}
        </span>
      </div>

      <p className="mt-3 text-xs text-slate-500 dark:text-white/50">
        {cita.motivo === 'expired'
          ? 'La hora pasó sin que se atendiera esta cita.'
          : [
              cita.canceladaEn ? `Cancelaste el ${cuando(cita.canceladaEn)}.` : '',
              cita.tardia ? 'Fue una cancelación tardía.' : '',
            ]
              .filter(Boolean)
              .join(' ')}
      </p>
    </li>
  )
}
