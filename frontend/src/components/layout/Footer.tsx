import { Link } from 'react-router-dom'
import { Logo } from './Logo'

export function Footer() {
  return (
    <footer className="bg-[#0B1B3A] text-slate-300">
      <div className="mx-auto grid max-w-6xl gap-10 px-4 py-12 sm:px-6 md:grid-cols-[1.5fr_1fr_1fr]">
        <div className="space-y-4">
          <Logo claro />
          <p className="max-w-sm text-sm leading-relaxed text-slate-400">
            El sistema operativo para barberías: agenda en tiempo real, caja diaria y
            comisiones en un solo lugar.
          </p>
        </div>

        <nav aria-label="Explorar">
          <h2 className="mb-4 font-[Barlow_Condensed] text-sm font-bold tracking-widest text-white uppercase">
            Explorar
          </h2>
          <ul className="space-y-3 text-sm">
            <li>
              <Link to="/reservar" className="hover:text-white">
                Reservar cita
              </Link>
            </li>
            <li>
              <a href="/#servicios" className="hover:text-white">
                Servicios
              </a>
            </li>
            <li>
              <a href="/#como-funciona" className="hover:text-white">
                Cómo funciona
              </a>
            </li>
          </ul>
        </nav>

        <nav aria-label="Cuenta">
          <h2 className="mb-4 font-[Barlow_Condensed] text-sm font-bold tracking-widest text-white uppercase">
            Cuenta
          </h2>
          <ul className="space-y-3 text-sm">
            <li>
              <Link to="/login" className="hover:text-white">
                Ingresar
              </Link>
            </li>
          </ul>
        </nav>
      </div>

      <div className="border-t border-white/10">
        <p className="mx-auto max-w-6xl px-4 py-5 text-xs text-slate-500 sm:px-6">
          © 2026 BarberFlow Technologies · Colombia
        </p>
      </div>
    </footer>
  )
}
