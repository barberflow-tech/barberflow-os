import { Menu, X } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { botonPrimario, botonSecundario } from '@/components/booking/wizard/estilos'
import { Logo } from './Logo'

export interface EnlaceNavbar {
  href: string
  etiqueta: string
}

interface NavbarProps {
  enlaces?: EnlaceNavbar[]
}

export function Navbar({ enlaces = [] }: NavbarProps) {
  const [abierto, setAbierto] = useState(false)

  return (
    <header className="sticky top-0 z-40 border-b border-slate-200 bg-white/90 backdrop-blur">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4 sm:px-6">
        <Logo />

        <nav aria-label="Principal" className="hidden items-center gap-8 md:flex">
          {enlaces.map((enlace) => (
            <a
              key={enlace.href}
              href={enlace.href}
              className="text-sm font-medium text-slate-600 transition-colors hover:text-[#0B1B3A]"
            >
              {enlace.etiqueta}
            </a>
          ))}
        </nav>

        <div className="hidden items-center gap-3 md:flex">
          <Link to="/login" className={botonSecundario}>
            Ingresar
          </Link>
          <Link to="/reservar" className={botonPrimario}>
            Reservar cita
          </Link>
        </div>

        <button
          type="button"
          onClick={() => setAbierto((v) => !v)}
          aria-expanded={abierto}
          aria-controls="menu-movil"
          aria-label={abierto ? 'Cerrar menú' : 'Abrir menú'}
          className="grid size-10 place-items-center rounded-xl border border-slate-200 text-[#0B1B3A] md:hidden"
        >
          {abierto ? (
            <X className="size-5" aria-hidden="true" />
          ) : (
            <Menu className="size-5" aria-hidden="true" />
          )}
        </button>
      </div>

      {abierto && (
        <div id="menu-movil" className="border-t border-slate-200 bg-white md:hidden">
          <nav aria-label="Principal móvil" className="flex flex-col gap-1 p-4">
            {enlaces.map((enlace) => (
              <a
                key={enlace.href}
                href={enlace.href}
                onClick={() => setAbierto(false)}
                className="rounded-lg px-3 py-3 text-sm font-medium text-slate-700 hover:bg-slate-50"
              >
                {enlace.etiqueta}
              </a>
            ))}
            <div className="mt-3 grid grid-cols-2 gap-3">
              <Link to="/login" className={botonSecundario}>
                Ingresar
              </Link>
              <Link to="/reservar" className={botonPrimario}>
                Reservar cita
              </Link>
            </div>
          </nav>
        </div>
      )}
    </header>
  )
}
