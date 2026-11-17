import { Menu, X } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { botonSecundario } from '@/components/booking/wizard/estilos'
import { useAuthStore, type Role } from '@/stores/useAuthStore'
import { Logo } from './Logo'

export interface EnlaceNavbar {
  href: string
  etiqueta: string
}

interface NavbarProps {
  enlaces?: EnlaceNavbar[]
}

// Pantalla propia de cada rol. El cliente gestiona sus citas desde su perfil.
const ENLACE_POR_ROL: Partial<Record<Role, { to: string; etiqueta: string }>> = {
  admin: { to: '/admin', etiqueta: 'Panel' },
  barbero: { to: '/barbero/portafolio', etiqueta: 'Mi portafolio' },
  cliente: { to: '/perfil', etiqueta: 'Mis citas' },
}

// Cerrar sesión va de último y en rojo vivo para que se note.
const botonCerrarSesion =
  'inline-flex h-11 items-center justify-center rounded-xl bg-[#E5283C] px-4 sm:px-5 text-sm font-semibold text-white shadow-md shadow-[#E5283C]/25 transition-colors hover:bg-[#C81F33] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#E5283C]'

/** Accesos de la derecha, según haya sesión o no. Reservar se hace desde cada página. */
function Accesos({ onNavegar }: { onNavegar?: () => void }) {
  const user = useAuthStore((s) => s.user)
  const logout = useAuthStore((s) => s.logout)
  const enlaceRol = user ? ENLACE_POR_ROL[user.role] : undefined

  return (
    <>
      {user ? (
        enlaceRol && (
          <Link to={enlaceRol.to} onClick={onNavegar} className={botonSecundario}>
            {enlaceRol.etiqueta}
          </Link>
        )
      ) : (
        <Link to="/login" onClick={onNavegar} className={botonSecundario}>
          Ingresar
        </Link>
      )}
      {user && (
        <button
          type="button"
          onClick={() => {
            onNavegar?.()
            void logout()
          }}
          className={botonCerrarSesion}
        >
          Cerrar sesión
        </button>
      )}
    </>
  )
}

export function Navbar({ enlaces = [] }: NavbarProps) {
  const [abierto, setAbierto] = useState(false)

  return (
    <header className="sticky top-0 z-40 border-b border-[#101820]/10 bg-[#FAFAF8]/92 backdrop-blur dark:border-[#F7F1E8]/10 dark:bg-[#101820]/92">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4 sm:px-6">
        <Logo />

        <nav aria-label="Principal" className="hidden items-center gap-8 md:flex">
          {enlaces.map((enlace) => (
            <a
              key={enlace.href}
              href={enlace.href}
              className="relative py-1 text-sm font-medium text-[#101820]/70 transition-colors after:absolute after:inset-x-0 after:-bottom-0.5 after:h-0.5 after:origin-left after:scale-x-0 after:bg-[#B3263B] after:transition-transform hover:text-[#101820] hover:after:scale-x-100 dark:text-[#F7F1E8]/70 dark:after:bg-[#E5283C] dark:hover:text-[#F7F1E8]"
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
          className="grid size-10 place-items-center rounded-xl border border-[#101820]/15 bg-[#FAFAF8] text-[#101820] dark:border-[#F7F1E8]/15 dark:bg-[#16202B] dark:text-[#F7F1E8] md:hidden"
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
          className="border-t border-[#101820]/10 bg-[#FAFAF8] dark:border-[#F7F1E8]/10 dark:bg-[#16202B] md:hidden"
        >
          <nav aria-label="Principal móvil" className="flex flex-col gap-1 p-4">
            {enlaces.map((enlace) => (
              <a
                key={enlace.href}
                href={enlace.href}
                onClick={() => setAbierto(false)}
                className="rounded-lg px-3 py-3 text-sm font-medium text-[#101820] transition-colors hover:bg-[#101820]/5 dark:text-[#F7F1E8]/85 dark:hover:bg-[#FAFAF8]/5"
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
