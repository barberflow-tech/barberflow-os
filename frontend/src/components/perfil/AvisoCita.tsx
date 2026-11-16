import { CheckCircle2, Info, X } from 'lucide-react'
import type { ReactNode } from 'react'
import { cn } from '@/lib/utils'

export type AvisoTipo = 'exito' | 'info'

export interface Aviso {
  tipo: AvisoTipo
  titulo: string
  detalle?: ReactNode
  /** Nota secundaria en ámbar: algo a tener en cuenta que no es un error. */
  nota?: ReactNode
}

/**
 * Resultado de una acción (cancelar, reprogramar). Es un aviso dentro de la
 * página y no un diálogo: la acción salió bien, no hay nada que «aceptar».
 */
export function AvisoCita({ aviso, onCerrar }: { aviso: Aviso; onCerrar: () => void }) {
  const exito = aviso.tipo === 'exito'
  const Icono = exito ? CheckCircle2 : Info

  return (
    <div
      role="status"
      className={cn(
        'mb-5 flex items-start gap-3 rounded-2xl border p-4',
        exito
          ? 'border-emerald-200 bg-emerald-50 dark:border-emerald-400/20 dark:bg-emerald-400/10'
          : 'border-slate-200 bg-white dark:border-white/10 dark:bg-[#151915]',
      )}
    >
      <span
        aria-hidden="true"
        className={cn(
          'mt-0.5 flex size-8 shrink-0 items-center justify-center rounded-full',
          exito
            ? 'bg-emerald-100 text-emerald-600 dark:bg-emerald-400/20 dark:text-emerald-300'
            : 'bg-slate-100 text-slate-500 dark:bg-white/10 dark:text-white/60',
        )}
      >
        <Icono className="size-4" />
      </span>
      <div className="min-w-0 flex-1">
        <p className="text-sm font-bold text-[#0B1B3A] dark:text-[#f4f1e9]">
          {aviso.titulo}
        </p>
        {aviso.detalle && (
          <p className="mt-0.5 text-sm text-slate-600 dark:text-white/65">
            {aviso.detalle}
          </p>
        )}
        {aviso.nota && (
          <p className="mt-2 rounded-lg bg-amber-50 px-3 py-2 text-xs font-medium text-amber-800 dark:bg-amber-400/10 dark:text-amber-200">
            {aviso.nota}
          </p>
        )}
      </div>
      <button
        type="button"
        aria-label="Cerrar aviso"
        onClick={onCerrar}
        className="flex size-7 shrink-0 items-center justify-center rounded-lg text-slate-400 transition-colors hover:bg-black/5 dark:text-white/40 dark:hover:bg-white/10"
      >
        <X className="size-4" aria-hidden="true" />
      </button>
    </div>
  )
}
