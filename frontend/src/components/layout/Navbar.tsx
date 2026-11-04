import { Menu, X } from 'lucide-react'
import { useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { botonPrimario, botonSecundario } from '@/components/booking/wizard/estilos'
import { useAuthStore, type Role } from '@/stores/useAuthStore'
import { Logo } from './Logo'

export interface EnlaceNavbar {
  href: string
  etiqueta: string
}

interface NavbarProps {
  enlaces?: EnlaceNavbar[]
}

// Pantalla propia de cada rol (el cliente no tiene panel: su espacio es la reserva).
const ENLACE_POR_ROL: Partial<Record<Role, { to: string; etiqueta: string }>> = {
  admin: { to: '/admin', etiqueta: 'Panel' },
  barbero: { to: '/barbero/portafolio', etiqueta: 'Mi portafolio' },
}

/** Accesos de la derecha: según haya sesión o no, y sin repetir la página actual. */
function Accesos({ onNavegar }: { onNavegar?: () => void }) {
  const user = useAuthStore((s) => s.user)
  const logout = useAuthStore((s) => s.logout)
  const { pathname } = useLocation()
  const enlaceRol = user ? ENLACE_POR_ROL[user.role] : undefined

  return (
    <>
      {user ? (
        <>
          {enlaceRol && (
            <Link to={enlaceRol.to} onClick={onNavegar} className={botonSecundario}>
              {enlaceRol.etiqueta}
            </Link>
          )}
          <button
            type="button"
            onClick={() => {
              onNavegar?.()
              void logout()
            }}
            className={botonSecundario}
          >
            Cerrar sesión
          </button>
        </>
      ) : (
        <Link to="/login" onClick={onNavegar} className={botonSecundario}>
          Ingresar
        </Link>
      )}
      {pathname !== '/reservar' && (
        <Link to="/reservar" onClick={onNavegar} className={botonPrimario}>
          Reservar cita
        </Link>
      )}
    </>
  )
}

export function Navbar({ enlaces = [] }: NavbarProps) {
  const [abierto, setAbierto] = useState(false)

  return (
    <header className="sticky top-0 z-40 border-b border-slate-200 dark:border-white/10 bg-white/90 dark:bg-[#0f1210]/90 backdrop-blur">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4 sm:px-6">
        <Logo />

        <nav aria-label="Principal" className="hidden items-center gap-8 md:flex">
          {enlaces.map((enlace) => (
            <a
              key={enlace.href}
              href={enlace.href}
              className="text-sm font-medium text-slate-600 dark:text-white/65 transition-colors hover:text-[#0B1B3A] dark:hover:text-[#f4f1e9]"
            >
              {enlace.etiqueta}
            </a>
          ))}
        </nav>

        <div className="hidden items-center gap-3 md:flex">
          <Accesos />
        </div>

        <button
          type="button"
          onClick={() => setAbierto((v) => !v)}
          aria-expanded={abierto}
          aria-controls="menu-movil"
          aria-label={abierto ? 'Cerrar menú' : 'Abrir menú'}
          className="grid size-10 place-items-center rounded-xl border border-slate-200 dark:border-white/10 text-[#0B1B3A] dark:text-[#f4f1e9] md:hidden"
        >
          {abierto ? (
            <X className="size-5" aria-hidden="true" />
          ) : (
            <Menu className="size-5" aria-hidden="true" />
          )}
        </button>
      </div>

      {abierto && (
        <div
          id="menu-movil"
          className="border-t border-slate-200 dark:border-white/10 bg-white dark:bg-[#151915] md:hidden"
        >
          <nav aria-label="Principal móvil" className="flex flex-col gap-1 p-4">
            {enlaces.map((enlace) => (
              <a
                key={enlace.href}
                href={enlace.href}
                onClick={() => setAbierto(false)}
                className="rounded-lg px-3 py-3 text-sm font-medium text-slate-700 dark:text-white/80 hover:bg-slate-50 dark:hover:bg-white/5"
              >
                {enlace.etiqueta}
              </a>
            ))}
            <div className="mt-3 grid grid-cols-2 gap-3">
              <Accesos onNavegar={() => setAbierto(false)} />
            </div>
          </nav>
        </div>
      )}
    </header>
  )
}
