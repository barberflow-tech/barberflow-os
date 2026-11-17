import { Scissors } from 'lucide-react'
import { Link } from 'react-router-dom'

interface LogoProps {
  /** Variante para fondos oscuros (footer, bandas navy). */
  claro?: boolean
}

/**
 * Marca BarberFlow: cuadrado grafito con borde marfil (como el letrero de la
 * barbería) y el nombre en Barlow Condensed. Funciona sobre fondo claro y
 * oscuro gracias a la prop `claro`.
 */
export function Logo({ claro = false }: LogoProps) {
  return (
    <Link
      to="/"
      aria-label="BarberFlow, ir al inicio"
      className="group flex items-center gap-3"
    >
      <span
        className={`grid size-10 place-items-center rounded-lg border shadow-md transition-transform duration-200 group-hover:-rotate-6 ${
          claro
            ? 'border-[#F7F1E8]/40 bg-[#101820] text-[#F7F1E8] shadow-black/30'
            : 'border-[#101820]/15 bg-[#101820] text-[#F7F1E8] shadow-[#101820]/20 dark:border-[#F7F1E8]/25 dark:shadow-black/40'
        }`}
      >
        <Scissors className="size-5" aria-hidden="true" />
      </span>
      <span className="leading-none">
        <span
          className={`block font-[Barlow_Condensed] text-xl font-bold tracking-wider uppercase ${
            claro ? 'text-[#F7F1E8]' : 'text-[#101820] dark:text-[#F7F1E8]'
          }`}
        >
          Barber<span className="text-[#B3263B] dark:text-[#E5283C]">Flow</span>
        </span>
        <span
          className={`block text-[10px] font-semibold tracking-[0.2em] uppercase ${
            claro ? 'text-[#F7F1E8]/55' : 'text-[#101820]/55 dark:text-[#F7F1E8]/55'
          }`}
        >
          Operating System
        </span>
      </span>
    </Link>
  )
}
