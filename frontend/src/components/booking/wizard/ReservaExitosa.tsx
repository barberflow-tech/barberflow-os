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
    <section className="relative overflow-hidden rounded-2xl border border-[#101820]/12 bg-[#F7F1E8] px-6 py-12 text-center shadow-[0_18px_40px_-22px_rgb(16_24_32_/_45%)] dark:border-[#F7F1E8]/12 dark:bg-[#16202B]">
      <div
        className="bf-patron-rayas pointer-events-none absolute inset-0 opacity-40"
        aria-hidden="true"
      />
      <div className="relative">
        <div
          aria-hidden="true"
          className="mx-auto flex size-16 items-center justify-center rounded-full border-2 border-[#10B981]/40 bg-[#10B981]/10 text-[#0b7a57] dark:text-[#34d399]"
        >
          <Check className="size-8" />
        </div>
        <h2 className={`${titulo} mt-5 text-3xl`}>¡Reserva confirmada!</h2>
        <p className="mx-auto mt-2 max-w-sm text-sm text-[#101820]/65 dark:text-[#F7F1E8]/65">
          Te esperamos el {fechaLarga(fecha)} a las {hora}. Te recordaremos 24 horas y 2
          horas antes.
        </p>
        <dl className="mx-auto mt-6 w-full max-w-sm space-y-2 rounded-2xl border border-dashed border-[#101820]/25 bg-[#101820] p-4 text-left text-xs text-[#F7F1E8] dark:border-[#F7F1E8]/25 dark:bg-[#0B1117]">
          <div className="flex justify-between gap-4">
            <dt className="text-[#F7F1E8]/65">Servicio</dt>
            <dd className="font-semibold text-[#F7F1E8]">{cita.servicio.nombre}</dd>
          </div>
          <div className="flex justify-between gap-4">
            <dt className="text-[#F7F1E8]/65">Profesional</dt>
            <dd className="font-semibold text-[#F7F1E8]">{cita.barbero.nombre}</dd>
          </div>
          <div className="flex justify-between border-t border-dashed border-[#F7F1E8]/25 pt-2">
            <dt className="text-[#F7F1E8]/65">Total</dt>
            <dd className="font-[Barlow_Condensed] text-lg font-bold text-[#F7F1E8]">
              {formatearPrecio(cita.total)}
            </dd>
          </div>
          <div className="text-[11px] text-[#F7F1E8]/45">Referencia BF-{cita.id}</div>
        </dl>
        <div className="mt-6 flex flex-col justify-center gap-2 sm:flex-row">
          <Link to="/" className={botonSecundario}>
            Volver al inicio
          </Link>
          <button type="button" onClick={onOtra} className={botonPrimario}>
            Reservar otra cita
          </button>
        </div>
      </div>
    </section>
  )
}
