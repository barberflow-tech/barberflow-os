import { Moon, Sun } from 'lucide-react'
import { useThemeStore } from '@/stores/useThemeStore'

/** Botón flotante para alternar entre modo claro (blanco y rojo) y oscuro (negro y dorado). */
export function ThemeToggle() {
  const tema = useThemeStore((s) => s.tema)
  const alternar = useThemeStore((s) => s.alternar)

  const oscuro = tema === 'dark'
  return (
    <button
      type="button"
      onClick={alternar}
      aria-label={oscuro ? 'Cambiar a modo claro' : 'Cambiar a modo oscuro'}
      title={oscuro ? 'Modo claro' : 'Modo oscuro'}
      className="fixed right-5 bottom-5 z-50 grid size-12 place-items-center rounded-full border border-slate-200 bg-white text-[#0B1B3A] shadow-lg transition hover:scale-105 dark:border-[#d7b36a]/50 dark:bg-[#151915] dark:text-[#d7b36a]"
    >
      {oscuro ? (
        <Sun className="size-5" aria-hidden="true" />
      ) : (
        <Moon className="size-5" aria-hidden="true" />
      )}
    </button>
  )
}
