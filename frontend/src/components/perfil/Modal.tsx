import { X } from 'lucide-react'
import { useEffect, useId, useRef, type ReactNode } from 'react'
import { cn } from '@/lib/utils'
import { titulo as claseTitulo } from '@/components/booking/wizard/estilos'

interface ModalProps {
  titulo: string
  subtitulo?: ReactNode
  onCerrar: () => void
  /** Deshabilita cerrar con Esc, clic fuera y la X (p. ej. mientras se envía). */
  bloqueado?: boolean
  ancho?: 'sm' | 'lg'
  children: ReactNode
}

/** Diálogo con la misma tarjeta, tipografía y paleta que el asistente de reserva. */
export function Modal({
  titulo,
  subtitulo,
  onCerrar,
  bloqueado = false,
  ancho = 'sm',
  children,
}: ModalProps) {
  const idTitulo = useId()
  const panel = useRef<HTMLDivElement>(null)

  useEffect(() => {
    panel.current?.focus()
    const alTeclear = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && !bloqueado) onCerrar()
    }
    document.addEventListener('keydown', alTeclear)
    return () => document.removeEventListener('keydown', alTeclear)
  }, [bloqueado, onCerrar])

  return (
    <div
      className="fixed inset-0 z-50 flex items-end justify-center bg-[#0B1B3A]/60 p-4 backdrop-blur-sm sm:items-center"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget && !bloqueado) onCerrar()
      }}
    >
      <div
        ref={panel}
        role="dialog"
        aria-modal="true"
        aria-labelledby={idTitulo}
        tabIndex={-1}
        className={cn(
          'max-h-[90vh] w-full overflow-y-auto rounded-2xl border border-slate-200 bg-white p-5 shadow-2xl outline-none dark:border-white/10 dark:bg-[#151915] sm:p-6',
          ancho === 'sm' ? 'max-w-md' : 'max-w-lg',
        )}
      >
        <header className="mb-4 flex items-start justify-between gap-4">
          <div>
            <h2 id={idTitulo} className={`${claseTitulo} text-2xl`}>
              {titulo}
            </h2>
            {subtitulo && (
              <p className="mt-0.5 text-sm text-slate-500 dark:text-white/55">
                {subtitulo}
              </p>
            )}
          </div>
          <button
            type="button"
            aria-label="Cerrar"
            disabled={bloqueado}
            onClick={onCerrar}
            className="flex size-8 shrink-0 items-center justify-center rounded-lg border border-slate-200 text-slate-500 transition-colors hover:bg-slate-50 disabled:opacity-40 dark:border-white/10 dark:text-white/55 dark:hover:bg-white/5"
          >
            <X className="size-4" aria-hidden="true" />
          </button>
        </header>
        {children}
      </div>
    </div>
  )
}
