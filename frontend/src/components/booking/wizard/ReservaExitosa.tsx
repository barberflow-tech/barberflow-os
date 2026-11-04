import { Check } from 'lucide-react'
import { Link } from 'react-router-dom'
import type { CitaConfirmada } from '@/lib/reservaApi'
import { botonPrimario, botonSecundario, titulo } from './estilos'
import { fechaLarga, formatearPrecio } from './formato'

export function ReservaExitosa({
  cita,
  onOtra,
}: {
  cita: CitaConfirmada
  onOtra: () => void
}) {
  const fecha = cita.inicio.slice(0, 10)
  const hora = cita.inicio.slice(11, 16)

  return (
    <section className="flex flex-col items-center rounded-2xl border border-slate-200 dark:border-white/10 bg-white dark:bg-[#151915] px-6 py-12 text-center shadow-sm">
      <div
        aria-hidden="true"
        className="flex size-14 items-center justify-center rounded-full bg-emerald-100 text-emerald-600"
      >
        <Check className="size-6" />
      </div>
      <h2 className={`${titulo} mt-5 text-3xl`}>¡Reserva confirmada!</h2>
      <p className="mt-2 max-w-sm text-sm text-slate-500 dark:text-white/55">
        Te esperamos el {fechaLarga(fecha)} a las {hora}. Te recordaremos 24 horas y 2
        horas antes.
      </p>
      <dl className="mt-6 w-full max-w-sm space-y-2 rounded-2xl bg-slate-50 dark:bg-white/5 p-4 text-left text-xs">
        <div className="flex justify-between gap-4">
          <dt className="text-slate-500 dark:text-white/55">Servicio</dt>
          <dd className="font-semibold text-[#0B1B3A] dark:text-[#f4f1e9]">
            {cita.servicio.nombre}
          </dd>
        </div>
        <div className="flex justify-between gap-4">
          <dt className="text-slate-500 dark:text-white/55">Profesional</dt>
          <dd className="font-semibold text-[#0B1B3A] dark:text-[#f4f1e9]">
            {cita.barbero.nombre}
          </dd>
        </div>
        <div className="flex justify-between border-t border-slate-200 dark:border-white/10 pt-2">
          <dt className="text-slate-500 dark:text-white/55">Total</dt>
          <dd className="font-bold text-[#0B1B3A] dark:text-[#f4f1e9]">
            {formatearPrecio(cita.total)}
          </dd>
        </div>
        <div className="text-[11px] text-slate-400 dark:text-white/40">
          Referencia BF-{cita.id}
        </div>
      </dl>
      <div className="mt-6 flex flex-col gap-2 sm:flex-row">
        <Link to="/" className={botonSecundario}>
          Volver al inicio
        </Link>
        <button type="button" onClick={onOtra} className={botonPrimario}>
          Reservar otra cita
        </button>
      </div>
    </section>
  )
}
