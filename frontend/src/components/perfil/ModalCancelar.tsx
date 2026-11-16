import { AlertTriangle } from 'lucide-react'
import type { CitaConfirmada } from '@/lib/reservaApi'
import { botonSecundario } from '@/components/booking/wizard/estilos'
import { fechaLocal } from '@/components/booking/wizard/formato'
import { Modal } from './Modal'
import { textoHoras } from './reglas'

interface Props {
  cita: CitaConfirmada
  /** Cancelar ahora se registraría como cancelación tardía. */
  tardia: boolean
  enviando: boolean
  error: string | null
  onConfirmar: () => void
  onCerrar: () => void
}

export function ModalCancelar({
  cita,
  tardia,
  enviando,
  error,
  onConfirmar,
  onCerrar,
}: Props) {
  const fecha = fechaLocal(cita.inicio.slice(0, 10)).toLocaleDateString('es-CO', {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
  })

  return (
    <Modal
      titulo="¿Cancelar esta cita?"
      subtitulo="Esta acción no se puede deshacer."
      onCerrar={onCerrar}
      bloqueado={enviando}
    >
      <dl className="space-y-2 rounded-xl bg-slate-50 p-4 text-sm dark:bg-white/5">
        <div className="flex justify-between gap-4">
          <dt className="text-slate-500 dark:text-white/55">Servicio</dt>
          <dd className="font-semibold text-[#0B1B3A] dark:text-[#f4f1e9]">
            {cita.servicio.nombre}
          </dd>
        </div>
        <div className="flex justify-between gap-4">
          <dt className="text-slate-500 dark:text-white/55">Barbero</dt>
          <dd className="font-semibold text-[#0B1B3A] dark:text-[#f4f1e9]">
            {cita.barbero.nombre}
          </dd>
        </div>
        <div className="flex justify-between gap-4">
          <dt className="text-slate-500 dark:text-white/55">Cuándo</dt>
          <dd className="text-right font-semibold capitalize text-[#0B1B3A] dark:text-[#f4f1e9]">
            {fecha} · {cita.inicio.slice(11, 16)}
          </dd>
        </div>
      </dl>

      {tardia && (
        <p className="mt-4 flex items-start gap-2 rounded-xl border border-amber-200 bg-amber-50 p-3 text-xs font-medium text-amber-800 dark:border-amber-400/20 dark:bg-amber-400/10 dark:text-amber-200">
          <AlertTriangle className="mt-px size-4 shrink-0" aria-hidden="true" />
          <span>
            Faltan menos de {textoHoras(cita.horasAntelacion)} para tu cita, así que
            quedará registrada como cancelación tardía.
          </span>
        </p>
      )}

      {error && (
        <p
          role="alert"
          className="mt-4 rounded-xl bg-[#FEF2F3] p-3 text-sm text-[#E5283C] dark:bg-red-400/10 dark:text-red-300"
        >
          {error}
        </p>
      )}

      <div className="mt-5 flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
        <button
          type="button"
          onClick={onCerrar}
          disabled={enviando}
          className={botonSecundario}
        >
          Volver
        </button>
        <button
          type="button"
          onClick={onConfirmar}
          disabled={enviando}
          className="inline-flex h-11 items-center justify-center rounded-xl bg-[#E5283C] px-5 text-sm font-semibold text-white shadow-md shadow-[#E5283C]/25 transition-colors hover:bg-[#cf1f33] disabled:opacity-60 dark:bg-red-500 dark:hover:bg-red-400"
        >
          {enviando ? 'Cancelando…' : 'Sí, cancelar cita'}
        </button>
      </div>
    </Modal>
  )
}
