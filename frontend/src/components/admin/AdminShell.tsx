import '@fontsource/dm-sans/400.css'
import '@fontsource/dm-sans/500.css'
import '@fontsource/dm-sans/600.css'
import '@fontsource/playfair-display/400.css'
import '@fontsource/playfair-display/400-italic.css'
import { LogOut } from 'lucide-react'
import type { ReactNode } from 'react'
import { Link, NavLink } from 'react-router-dom'
import { cn } from '@/lib/utils'
import { useAuthStore } from '@/stores/useAuthStore'

const enlaces = [
  { to: '/admin', etiqueta: 'Panel', fin: true },
  { to: '/admin/servicios', etiqueta: 'Servicios', fin: false },
  { to: '/admin/barberos', etiqueta: 'Barberos', fin: false },
]

/** Marco común del área de administración (mismo estilo oscuro y dorado del portafolio). */
export function AdminShell({ children }: { children: ReactNode }) {
  const user = useAuthStore((state) => state.user)
  const logout = useAuthStore((state) => state.logout)

  return (
    <div className="min-h-screen bg-app font-['DM_Sans',sans-serif] text-app-fg">
      <header className="border-b border-app-fg/10">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-4 px-5 py-4 sm:px-8 lg:px-12">
          <Link to="/admin" className="flex items-center gap-3">
            <span className="grid size-10 place-items-center rounded-full border border-brand/50 text-brand">
              <span className="font-['Playfair_Display',serif] text-lg">BF</span>
            </span>
            <span>
              <span className="block text-sm font-semibold tracking-[0.08em] text-app-fg">
                BARBERFLOW
              </span>
              <span className="block text-[0.65rem] tracking-[0.22em] text-app-fg/45 uppercase">
                OS · Administración
              </span>
            </span>
          </Link>

          <nav aria-label="Secciones del panel" className="flex items-center gap-1">
            {enlaces.map(({ to, etiqueta, fin }) => (
              <NavLink
                key={to}
                to={to}
                end={fin}
                className={({ isActive }) =>
                  cn(
                    'rounded-full px-4 py-2 text-sm font-medium transition',
                    isActive
                      ? 'bg-brand text-brand-fg'
                      : 'text-app-fg/65 hover:bg-app-fg/5 hover:text-app-fg',
                  )
                }
              >
                {etiqueta}
              </NavLink>
            ))}
          </nav>

          <div className="flex items-center gap-3 text-sm">
            <span className="hidden text-app-fg/50 sm:inline">{user?.email}</span>
            <button
              type="button"
              onClick={() => void logout()}
              className="inline-flex items-center gap-2 rounded-full border border-app-fg/15 px-4 py-2 font-medium text-app-fg/80 transition hover:border-brand/60 hover:text-app-fg"
            >
              <LogOut className="size-4" aria-hidden="true" />
              Cerrar sesión
            </button>
          </div>
        </div>
      </header>

      <div className="mx-auto max-w-7xl px-5 py-10 sm:px-8 sm:py-14 lg:px-12">
        {children}
      </div>
    </div>
  )
}
