import { Scissors } from 'lucide-react'
import { Link } from 'react-router-dom'

interface LogoProps {
  /** Variante para fondos oscuros (footer, bandas navy). */
  claro?: boolean
}

export function Logo({ claro = false }: LogoProps) {
  return (
    <Link
      to="/"
      aria-label="BarberFlow, ir al inicio"
      className="flex items-center gap-3"
    >
      <span className="grid size-10 place-items-center rounded-xl bg-[#E5283C] dark:bg-[#d7b36a] text-white dark:text-[#111411] shadow-md shadow-[#E5283C]/25 dark:shadow-[#d7b36a]/20">
        <Scissors className="size-5" aria-hidden="true" />
      </span>
      <span className="leading-none">
        <span
          className={`block font-[Barlow_Condensed] text-xl font-bold tracking-wider uppercase ${
            claro ? 'text-white' : 'text-[#0B1B3A] dark:text-[#f4f1e9]'
          }`}
        >
          Barber<span className="text-[#E5283C] dark:text-[#d7b36a]">Flow</span>
        </span>
        <span
          className={`block text-[10px] font-semibold tracking-[0.2em] uppercase ${
            claro
              ? 'text-slate-400 dark:text-white/40'
              : 'text-slate-500 dark:text-white/55'
          }`}
        >
          Operating System
        </span>
      </span>
    </Link>
  )
}
