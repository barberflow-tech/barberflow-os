import { Link } from 'react-router-dom'
import { Logo } from './Logo'

/**
 * Pie de página de las pantallas públicas: banda grafito con la franja de
 * poste barbero arriba y títulos en Barlow Condensed con línea de acento.
 */
export function Footer() {
  return (
    <footer className="bg-[#101820] text-[#F7F1E8]/75 dark:bg-[#0B1117]">
      {/* Franja del poste de barbería. */}
      <div className="bf-poste h-[18px]" aria-hidden="true" />

      <div className="mx-auto grid max-w-6xl gap-10 px-4 py-12 sm:px-6 md:grid-cols-[1.5fr_1fr_1fr]">
        <div className="space-y-4">
          <Logo claro />
          <p className="max-w-sm text-sm leading-relaxed text-[#F7F1E8]/55">
            El sistema operativo para barberías: agenda en tiempo real, caja diaria y
            comisiones en un solo lugar.
          </p>
        </div>

        <nav aria-label="Explorar">
          <h2 className="bf-etiqueta mb-4 inline-block font-[Barlow_Condensed] text-sm font-bold tracking-widest text-[#F7F1E8] uppercase">
            Explorar
          </h2>
          <ul className="space-y-3 text-sm">
            <li>
              <Link to="/reservar" className="transition-colors hover:text-[#F7F1E8]">
                Reservar cita
              </Link>
            </li>
            <li>
              <a href="/#servicios" className="transition-colors hover:text-[#F7F1E8]">
                Servicios
              </a>
            </li>
            <li>
              <a
                href="/#como-funciona"
                className="transition-colors hover:text-[#F7F1E8]"
              >
                Cómo funciona
              </a>
            </li>
          </ul>
        </nav>

        <nav aria-label="Cuenta">
          <h2 className="bf-etiqueta mb-4 inline-block font-[Barlow_Condensed] text-sm font-bold tracking-widest text-[#F7F1E8] uppercase">
            Cuenta
          </h2>
          <ul className="space-y-3 text-sm">
            <li>
              <Link to="/login" className="transition-colors hover:text-[#F7F1E8]">
                Ingresar
              </Link>
            </li>
          </ul>
        </nav>
      </div>

      <div className="border-t border-[#F7F1E8]/10">
        <p className="mx-auto max-w-6xl px-4 py-5 text-xs text-[#F7F1E8]/45 sm:px-6">
          © 2026 BarberFlow Technologies · Colombia
        </p>
      </div>
    </footer>
  )
}
