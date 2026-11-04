import '@fontsource-variable/inter'
import '@fontsource/barlow-condensed/600.css'
import '@fontsource/barlow-condensed/700.css'
import {
  ArrowRight,
  CalendarClock,
  Check,
  ShieldCheck,
  UserRound,
  Wallet,
} from 'lucide-react'
import { Link } from 'react-router-dom'
import {
  botonPrimario,
  botonSecundario,
  titulo,
} from '@/components/booking/wizard/estilos'
import { ListaServicios } from '@/components/inicio/ListaServicios'
import { Footer } from '@/components/layout/Footer'
import { Navbar, type EnlaceNavbar } from '@/components/layout/Navbar'

const enlaces: EnlaceNavbar[] = [
  { href: '#servicios', etiqueta: 'Servicios' },
  { href: '#como-funciona', etiqueta: 'Cómo funciona' },
  { href: '#beneficios', etiqueta: 'Beneficios' },
]

const pasos = [
  { titulo: 'Elige el servicio', detalle: 'Corte, barba o ambos.' },
  { titulo: 'Escoge tu barbero', detalle: 'Mira quién atiende y su calificación.' },
  {
    titulo: 'Selecciona fecha y hora',
    detalle: 'Solo ves los horarios realmente libres.',
  },
  { titulo: 'Confirma', detalle: 'Recibes tu reserva en segundos.' },
]

const beneficios = [
  {
    icono: CalendarClock,
    titulo: 'Agenda en tiempo real',
    detalle:
      'Cada cita reservada aparece al instante en la agenda de la barbería, sin cruces ni llamadas.',
  },
  {
    icono: ShieldCheck,
    titulo: 'Menos ausencias',
    detalle:
      'SmartGuard anticipa qué citas tienen riesgo de ausencia y pide confirmación a tiempo.',
  },
  {
    icono: Wallet,
    titulo: 'Caja y comisiones',
    detalle:
      'Cobros, cierre de caja y liquidación de comisiones por barbero sin hojas de cálculo.',
  },
]

const horasEjemplo = [
  { hora: '09:00', estado: 'libre' },
  { hora: '09:30', estado: 'ocupada' },
  { hora: '10:00', estado: 'libre' },
  { hora: '10:30', estado: 'elegida' },
]

export function InicioPage() {
  return (
    <div className="min-h-screen bg-[#F1F5F9] dark:bg-[#0f1210] font-[Inter_Variable] text-[#0B1B3A] dark:text-[#f4f1e9]">
      <Navbar enlaces={enlaces} />

      <main>
        {/* Hero */}
        <section className="bg-white dark:bg-[#151915]">
          <div className="mx-auto grid max-w-6xl items-center gap-12 px-4 py-16 sm:px-6 lg:grid-cols-2 lg:py-24">
            <div className="space-y-6">
              <p className="inline-flex items-center gap-2 rounded-full border border-slate-200 dark:border-white/10 bg-slate-50 dark:bg-white/5 px-3 py-1 text-xs font-semibold tracking-wider text-slate-600 dark:text-white/65 uppercase">
                <span className="size-2 rounded-full bg-[#10B981]" aria-hidden="true" />
                Reservas en línea 24/7
              </p>
              <h1 className={`${titulo} text-5xl leading-[1.05] sm:text-6xl`}>
                Tu barbería,{' '}
                <span className="text-[#E5283C] dark:text-[#d7b36a]">
                  bajo control.
                </span>
              </h1>
              <p className="max-w-lg text-lg leading-relaxed text-slate-600 dark:text-white/65">
                Reserva tu cita en pocos pasos y deja que la barbería gestione su
                agenda, su caja y su equipo desde un solo sistema.
              </p>
              <div className="flex flex-col gap-3 sm:flex-row">
                <Link to="/reservar" className={`${botonPrimario} h-12 px-6`}>
                  Reservar cita
                  <ArrowRight className="size-4" aria-hidden="true" />
                </Link>
                <Link to="/login" className={`${botonSecundario} h-12 px-6`}>
                  Ingresar
                </Link>
              </div>
            </div>

            {/* Tarjeta decorativa que imita el asistente de reserva */}
            <div aria-hidden="true" className="relative mx-auto w-full max-w-md">
              <div className="absolute -inset-4 rounded-[2rem] bg-[#E5283C]/10 dark:bg-[#d7b36a]/10 blur-2xl" />
              <div className="relative space-y-5 rounded-2xl border border-slate-200 dark:border-white/10 bg-white dark:bg-[#151915] p-6 shadow-xl">
                <div className="flex items-center gap-3">
                  <span className="grid size-11 place-items-center rounded-full bg-[#0B1B3A] dark:bg-[#171c17] text-sm font-bold text-white">
                    TH
                  </span>
                  <div>
                    <p className="font-semibold">Thiago</p>
                    <p className="text-xs text-slate-500 dark:text-white/55">
                      Master barber · 4.9 ★
                    </p>
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  {horasEjemplo.map(({ hora, estado }) => (
                    <span
                      key={hora}
                      className={`rounded-xl border px-4 py-3 text-center text-sm font-semibold ${
                        estado === 'elegida'
                          ? 'border-[#E5283C] dark:border-[#d7b36a] bg-[#FEF2F3] dark:bg-[#d7b36a]/10 text-[#E5283C] dark:text-[#d7b36a]'
                          : estado === 'ocupada'
                            ? 'border-slate-100 dark:border-white/5 bg-slate-50 dark:bg-white/5 text-slate-300 dark:text-white/30 line-through'
                            : 'border-slate-200 dark:border-white/10 text-[#0B1B3A] dark:text-[#f4f1e9]'
                      }`}
                    >
                      {hora}
                    </span>
                  ))}
                </div>
                <p className="flex items-center gap-2 rounded-xl bg-[#10B981]/10 px-4 py-3 text-sm font-semibold text-[#0b7a57]">
                  <Check className="size-4" /> Cita confirmada
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* Servicios */}
        <section id="servicios" className="scroll-mt-16 py-16 sm:py-20">
          <div className="mx-auto max-w-6xl px-4 sm:px-6">
            <h2 className={`${titulo} text-3xl sm:text-4xl`}>Nuestros servicios</h2>
            <p className="mt-2 max-w-xl text-slate-600 dark:text-white/65">
              Lo que puedes reservar hoy. Elige el que necesitas y escoge tu horario.
            </p>
            <ListaServicios />
          </div>
        </section>

        {/* Cómo funciona */}
        <section
          id="como-funciona"
          className="scroll-mt-16 bg-white dark:bg-[#151915] py-16 sm:py-20"
        >
          <div className="mx-auto max-w-6xl px-4 sm:px-6">
            <h2 className={`${titulo} text-3xl sm:text-4xl`}>Cómo funciona</h2>
            <p className="mt-2 max-w-xl text-slate-600 dark:text-white/65">
              Cuatro pasos, sin llamadas ni mensajes de ida y vuelta.
            </p>
            <ol className="mt-10 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
              {pasos.map((paso, i) => (
                <li key={paso.titulo} className="space-y-3">
                  <span className="grid size-10 place-items-center rounded-full bg-[#0B1B3A] dark:bg-[#171c17] font-[Barlow_Condensed] text-lg font-bold text-white">
                    {i + 1}
                  </span>
                  <h3 className="font-semibold">{paso.titulo}</h3>
                  <p className="text-sm text-slate-600 dark:text-white/65">
                    {paso.detalle}
                  </p>
                </li>
              ))}
            </ol>
          </div>
        </section>

        {/* Beneficios */}
        <section id="beneficios" className="scroll-mt-16 py-16 sm:py-20">
          <div className="mx-auto max-w-6xl px-4 sm:px-6">
            <h2 className={`${titulo} text-3xl sm:text-4xl`}>
              Pensado para barberías de 3 a 10 sillas
            </h2>
            <ul className="mt-10 grid gap-4 md:grid-cols-3">
              {beneficios.map(({ icono: Icono, titulo: nombre, detalle }) => (
                <li
                  key={nombre}
                  className="space-y-3 rounded-xl border bg-white dark:bg-[#151915] p-6"
                >
                  <span className="grid size-11 place-items-center rounded-xl bg-[#0B1B3A] dark:bg-[#171c17] text-white">
                    <Icono className="size-5" aria-hidden="true" />
                  </span>
                  <h3 className="text-lg font-semibold">{nombre}</h3>
                  <p className="text-sm leading-relaxed text-slate-600 dark:text-white/65">
                    {detalle}
                  </p>
                </li>
              ))}
            </ul>
          </div>
        </section>

        {/* Llamado final */}
        <section className="pb-16 sm:pb-20">
          <div className="mx-auto max-w-6xl px-4 sm:px-6">
            <div className="flex flex-col items-start justify-between gap-6 rounded-2xl bg-[#0B1B3A] dark:bg-[#171c17] p-8 text-white sm:p-12 md:flex-row md:items-center">
              <div>
                <h2 className="font-[Barlow_Condensed] text-3xl font-bold tracking-wide uppercase sm:text-4xl">
                  ¿Listo para tu próximo corte?
                </h2>
                <p className="mt-2 text-slate-300 dark:text-white/65">
                  Agenda en menos de un minuto y llega sin esperas.
                </p>
              </div>
              <Link to="/reservar" className={`${botonPrimario} h-12 shrink-0 px-6`}>
                <UserRound className="size-4" aria-hidden="true" />
                Reservar ahora
              </Link>
            </div>
          </div>
        </section>
      </main>

      <Footer />
    </div>
  )
}

export default InicioPage
