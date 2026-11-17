import { CheckCircle2, X } from 'lucide-react'
import { useEffect } from 'react'
import { useAuthStore } from '@/stores/useAuthStore'

/** Segundos que el aviso permanece en pantalla antes de irse solo. */
const VISIBLE_MS = 6000

/**
 * Aviso flotante tras cerrar sesión. Vive en la raíz de la app y no en la barra:
 * al cerrar sesión se cambia de página y la barra que lo disparó desaparece.
 */
export function AvisoSesionCerrada() {
  const visible = useAuthStore((s) => s.sesionCerrada)
  const descartar = useAuthStore((s) => s.descartarSesionCerrada)

  useEffect(() => {
    if (!visible) return
    const id = setTimeout(descartar, VISIBLE_MS)
    return () => clearTimeout(id)
  }, [visible, descartar])

  if (!visible) return null

  return (
    <div className="pointer-events-none fixed inset-x-0 top-20 z-50 flex justify-center px-4">
      <div
        role="status"
        className="pointer-events-auto flex w-full max-w-md items-start gap-3 rounded-2xl border border-emerald-200 bg-emerald-50 p-4 shadow-lg dark:border-emerald-400/25 dark:bg-[#12261d]"
      >
        <span
          aria-hidden="true"
          className="mt-0.5 flex size-8 shrink-0 items-center justify-center rounded-full bg-emerald-100 text-emerald-600 dark:bg-emerald-400/20 dark:text-emerald-300"
        >
          <CheckCircle2 className="size-4" />
        </span>
        <div className="min-w-0 flex-1">
          <p className="text-sm font-bold text-[#101820] dark:text-[#F7F1E8]">
            Tu sesión se ha cerrado exitosamente
          </p>
          <p className="mt-0.5 text-sm text-[#101820]/70 dark:text-[#F7F1E8]/70">
            ¡Vuelve pronto!
          </p>
        </div>
        <button
          type="button"
          aria-label="Cerrar aviso"
          onClick={descartar}
          className="rounded-lg p-1 text-[#101820]/50 transition-colors hover:text-[#101820] dark:text-[#F7F1E8]/50 dark:hover:text-[#F7F1E8]"
        >
          <X className="size-4" aria-hidden="true" />
        </button>
      </div>
    </div>
  )
}
