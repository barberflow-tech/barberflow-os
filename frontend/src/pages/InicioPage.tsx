import '@fontsource-variable/inter'
import '@fontsource/barlow-condensed/600.css'
import '@fontsource/barlow-condensed/700.css'
import {
  ArrowRight,
  CalendarClock,
  Check,
  Scissors,
  ShieldCheck,
  SlidersHorizontal,
  Sparkles,
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
    <div className="min-h-screen bg-[#F7F1E8] font-[Inter_Variable] text-[#101820] dark:bg-[#101820] dark:text-[#F7F1E8]">
      <Navbar enlaces={enlaces} />

      <main>
        {/* Hero: grafito con grano y rayas de poste, como el interior de la barbería */}
        <section className="relative overflow-hidden bg-[#101820] text-[#F7F1E8] dark:bg-[#0B1117]">
          <div
            className="bf-grano pointer-events-none absolute inset-0"
            aria-hidden="true"
          />
          <div
            className="bf-patron-rayas pointer-events-none absolute inset-0 opacity-70"
            aria-hidden="true"
          />
          {/* Tijera decorativa de fondo */}
          <Scissors
            className="pointer-events-none absolute -right-10 top-8 size-64 rotate-12 text-[#F7F1E8]/[0.04] sm:size-80"
            aria-hidden="true"
          />
          <SlidersHorizontal
            className="pointer-events-none absolute -left-8 bottom-6 size-40 -rotate-12 text-[#B3263B]/20 sm:size-52"
            aria-hidden="true"
          />

          <div className="relative mx-auto grid max-w-6xl items-center gap-12 px-4 py-16 sm:px-6 lg:grid-cols-2 lg:py-24">
            <div className="space-y-6">
              <p className="inline-flex items-center gap-2 rounded-full border border-[#F7F1E8]/20 bg-[#F7F1E8]/5 px-3 py-1 text-xs font-semibold tracking-wider text-[#F7F1E8]/80 uppercase">
                <span className="size-2 rounded-full bg-[#10B981]" aria-hidden="true" />
                Reservas en línea 24/7
              </p>
              <h1
                className={`${titulo} text-5xl leading-[1.05] text-[#F7F1E8]! sm:text-6xl`}
              >
                Tu barbería,{' '}
                <span className="text-[#E5283C] dark:text-[#E5283C]">
                  bajo control.
                </span>
              </h1>
              {/* Poste de barbería como detalle del oficio */}
              <div
                className="bf-poste h-[18px] w-40 rounded-sm opacity-90"
                aria-hidden="true"
              />
              <p className="max-w-lg text-lg leading-relaxed text-[#F7F1E8]/70">
                Reserva tu cita en pocos pasos y deja que la barbería gestione su
                agenda, su caja y su equipo desde un solo sistema.
              </p>
              <div className="flex flex-col gap-3 sm:flex-row">
                <Link to="/reservar" className={`${botonPrimario} h-12 px-6`}>
                  Reservar cita
                  <ArrowRight className="size-4" aria-hidden="true" />
                </Link>
                <Link
                  to="/login"
                  className={`${botonSecundario} h-12 border-[#F7F1E8]/25 bg-transparent! px-6 text-[#F7F1E8]! hover:bg-[#F7F1E8]/10 dark:border-[#F7F1E8]/25 dark:bg-transparent! dark:hover:bg-[#F7F1E8]/10`}
                >
                  Ingresar
                </Link>
              </div>
            </div>

            {/* Tarjeta decorativa que imita el asistente de reserva (estilo ticket) */}
            <div aria-hidden="true" className="relative mx-auto w-full max-w-md">
              <div className="absolute -inset-4 rounded-[2rem] bg-[#B3263B]/20 blur-2xl" />
              <div className="bf-marco relative space-y-5 rounded-2xl bg-[#F7F1E8] p-6 text-[#101820] shadow-2xl dark:bg-[#16202B] dark:text-[#F7F1E8]">
                <div className="flex items-center gap-3 border-b border-dashed border-[#101820]/20 pb-4 dark:border-[#F7F1E8]/20">
                  <span className="grid size-11 place-items-center rounded-full bg-[#101820] text-sm font-bold text-[#F7F1E8] dark:bg-[#F7F1E8] dark:text-[#101820]">
                    TH
                  </span>
                  <div>
                    <p className="font-semibold">Thiago</p>
                    <p className="text-xs text-[#101820]/60 dark:text-[#F7F1E8]/60">
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
                          ? 'border-[#B3263B] bg-[#FBEEF0] text-[#B3263B] dark:border-[#E5283C] dark:bg-[#E5283C]/10 dark:text-[#E5283C]'
                          : estado === 'ocupada'
                            ? 'border-[#101820]/5 bg-[#101820]/5 text-[#101820]/30 line-through dark:border-white/5 dark:bg-white/5 dark:text-white/30'
                            : 'border-[#101820]/15 text-[#101820] dark:border-[#F7F1E8]/15 dark:text-[#F7F1E8]'
                      }`}
                    >
                      {hora}
                    </span>
                  ))}
                </div>
                <p className="flex items-center gap-2 rounded-xl bg-[#10B981]/10 px-4 py-3 text-sm font-semibold text-[#0b7a57] dark:text-[#34d399]">
                  <Check className="size-4" /> Cita confirmada
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* Servicios */}
        <section id="servicios" className="scroll-mt-16 py-16 sm:py-20">
          <div className="mx-auto max-w-6xl px-4 sm:px-6">
            <span className="inline-flex items-center gap-2 text-xs font-semibold tracking-widest text-[#B3263B] uppercase dark:text-[#E5283C]">
              <Scissors className="size-4" aria-hidden="true" />
              El catálogo
            </span>
            <h2 className={`${titulo} bf-etiqueta mt-2 text-3xl sm:text-4xl`}>
              Nuestros servicios
            </h2>
            <p className="mt-3 max-w-xl text-[#101820]/70 dark:text-[#F7F1E8]/70">
              Lo que puedes reservar hoy. Elige el que necesitas y escoge tu horario.
            </p>
            <ListaServicios />
          </div>
        </section>

        {/* Cómo funciona */}
        <section
          id="como-funciona"
          className="scroll-mt-16 border-y border-[#101820]/10 bg-[#F7F1E8] py-16 sm:py-20 dark:border-[#F7F1E8]/10 dark:bg-[#16202B]"
        >
          <div className="mx-auto max-w-6xl px-4 sm:px-6">
            <span className="inline-flex items-center gap-2 text-xs font-semibold tracking-widest text-[#174A7E] uppercase dark:text-[#5FA3E0]">
              <SlidersHorizontal className="size-4" aria-hidden="true" />
              El método
            </span>
            <h2 className={`${titulo} bf-etiqueta mt-2 text-3xl sm:text-4xl`}>
              Cómo funciona
            </h2>
            <p className="mt-3 max-w-xl text-[#101820]/70 dark:text-[#F7F1E8]/70">
              Cuatro pasos, sin llamadas ni mensajes de ida y vuelta.
            </p>
            <ol className="mt-10 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
              {pasos.map((paso, i) => (
                <li
                  key={paso.titulo}
                  className="bf-tarjeta space-y-3 border-t-4 border-t-[#B3263B] p-6 dark:border-t-[#E5283C] dark:bg-[#101820]"
                >
                  <span className="grid size-10 place-items-center rounded-full border-2 border-[#B3263B] font-[Barlow_Condensed] text-lg font-bold text-[#B3263B] dark:border-[#E5283C] dark:text-[#E5283C]">
                    {i + 1}
                  </span>
                  <h3 className="font-[Barlow_Condensed] text-lg font-bold tracking-wide text-[#101820] uppercase dark:text-[#F7F1E8]">
                    {paso.titulo}
                  </h3>
                  <p className="text-sm text-[#101820]/70 dark:text-[#F7F1E8]/70">
                    {paso.detalle}
                  </p>
                </li>
              ))}
            </ol>
          </div>
        </section>

        {/* Beneficios: banda grafito */}
        <section
          id="beneficios"
          className="scroll-mt-16 bg-[#101820] py-16 text-[#F7F1E8] sm:py-20 dark:bg-[#0B1117]"
        >
          <div className="mx-auto max-w-6xl px-4 sm:px-6">
            <span className="inline-flex items-center gap-2 text-xs font-semibold tracking-widest text-[#E5283C] uppercase">
              <Sparkles className="size-4" aria-hidden="true" />
              Por qué BarberFlow
            </span>
            <h2
              className={`${titulo} bf-etiqueta mt-2 text-3xl text-[#F7F1E8]! sm:text-4xl`}
            >
              Pensado para barberías de 3 a 10 sillas
            </h2>
            <ul className="mt-10 grid gap-4 md:grid-cols-3">
              {beneficios.map(({ icono: Icono, titulo: nombre, detalle }) => (
                <li
                  key={nombre}
                  className="space-y-3 rounded-[14px] border border-[#F7F1E8]/12 bg-[#16202B] p-6 transition-colors hover:border-[#E5283C]/50"
                >
                  <span className="grid size-11 place-items-center rounded-xl border border-[#E5283C]/40 bg-[#E5283C]/10 text-[#E5283C]">
                    <Icono className="size-5" aria-hidden="true" />
                  </span>
                  <h3 className="font-[Barlow_Condensed] text-lg font-bold tracking-wide uppercase">
                    {nombre}
                  </h3>
                  <p className="text-sm leading-relaxed text-[#F7F1E8]/70">{detalle}</p>
                </li>
              ))}
            </ul>
          </div>
        </section>

        {/* Llamado final */}
        <section className="bg-[#F7F1E8] pb-16 sm:pb-20 dark:bg-[#101820]">
          <div className="mx-auto max-w-6xl px-4 sm:px-6">
            <div className="bf-marco relative flex flex-col items-start justify-between gap-6 overflow-hidden rounded-2xl bg-[#174A7E] p-8 text-[#F7F1E8] sm:p-12 md:flex-row md:items-center">
              <div
                className="bf-patron-rayas pointer-events-none absolute inset-0 opacity-60"
                aria-hidden="true"
              />
              <div className="relative">
                <h2 className="font-[Barlow_Condensed] text-3xl font-bold tracking-wide uppercase sm:text-4xl">
                  ¿Listo para tu próximo corte?
                </h2>
                <p className="mt-2 text-[#F7F1E8]/80">
                  Agenda en menos de un minuto y llega sin esperas.
                </p>
              </div>
              <Link
                to="/reservar"
                className={`${botonPrimario} relative h-12 shrink-0 px-6`}
              >
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
