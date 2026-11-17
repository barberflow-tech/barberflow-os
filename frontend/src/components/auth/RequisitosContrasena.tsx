import { Check, Circle } from 'lucide-react'
import { REQUISITOS_CONTRASENA } from '@/lib/requisitosContrasena'

/** Lista de requisitos de la contraseña: cada uno se pone verde al cumplirse. */
export function RequisitosContrasena({ contrasena }: { contrasena: string }) {
  return (
    <ul
      aria-label="Requisitos de la contraseña"
      className="grid gap-1 pt-1 sm:grid-cols-2"
    >
      {REQUISITOS_CONTRASENA.map(({ id, texto, cumple }) => {
        const cumplido = cumple(contrasena)
        return (
          <li
            key={id}
            data-cumplido={cumplido}
            className={`flex items-center gap-1.5 text-xs transition-colors ${
              cumplido
                ? 'font-semibold text-[#0b7a57] dark:text-[#34d399]'
                : 'text-[#101820]/55 dark:text-[#F7F1E8]/55'
            }`}
          >
            {cumplido ? (
              <Check className="size-3.5 shrink-0" aria-hidden="true" />
            ) : (
              <Circle className="size-3.5 shrink-0" aria-hidden="true" />
            )}
            <span>{texto}</span>
            <span className="sr-only">{cumplido ? ' (cumplido)' : ' (pendiente)'}</span>
          </li>
        )
      })}
    </ul>
  )
}
