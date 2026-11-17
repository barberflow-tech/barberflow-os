import { useState } from 'react'
import { ArrowRight, Check } from 'lucide-react'
import { crearCita } from '@/lib/reservaApi'
import { useReservaWizardStore, type PasoReserva } from '@/stores/useReservaWizardStore'
import { cn } from '@/lib/utils'
import type { ClienteData } from '@/lib/reservaSchema'
import { PasoBarbero } from './PasoBarbero'
import { PasoConfirmar } from './PasoConfirmar'
import { PasoFechaHora } from './PasoFechaHora'
import { PasoServicio } from './PasoServicio'
import { botonPrimario, botonSecundario } from './estilos'
import { construirInicio } from './formato'
import { ReservaExitosa } from './ReservaExitosa'

const PASOS: { n: PasoReserva; titulo: string }[] = [
  { n: 1, titulo: 'Servicio' },
  { n: 2, titulo: 'Barbero' },
  { n: 3, titulo: 'Fecha y hora' },
  { n: 4, titulo: 'Confirmar' },
]

const ENCABEZADOS: Record<PasoReserva, { titulo: string; subtitulo: string }> = {
  1: {
    titulo: '¿Qué servicio deseas reservar?',
    subtitulo: 'Selecciona una opción para continuar',
  },
  2: {
    titulo: 'Elige tu barbero',
    subtitulo: 'Todos son especialistas en tu servicio',
  },
  3: {
    titulo: 'Selecciona fecha y hora',
    subtitulo: 'Disponibilidad del barbero elegido',
  },
  4: {
    titulo: 'Confirma tu reserva',
    subtitulo: 'Revisa los datos antes de finalizar',
  },
}

export function ReservaWizard() {
  const paso = useReservaWizardStore((s) => s.paso)
  const cita = useReservaWizardStore((s) => s.cita)
  const servicio = useReservaWizardStore((s) => s.servicio)
  const barbero = useReservaWizardStore((s) => s.barbero)
  const fecha = useReservaWizardStore((s) => s.fecha)
  const hora = useReservaWizardStore((s) => s.hora)
  const siguiente = useReservaWizardStore((s) => s.siguiente)
  const atras = useReservaWizardStore((s) => s.atras)
  const registrarCita = useReservaWizardStore((s) => s.registrarCita)
  const reiniciar = useReservaWizardStore((s) => s.reiniciar)
  const [enviando, setEnviando] = useState(false)
  const [error, setError] = useState<string | null>(null)

  if (cita) return <ReservaExitosa cita={cita} onOtra={reiniciar} />

  const puedeContinuar =
    (paso === 1 && !!servicio) ||
    (paso === 2 && !!barbero) ||
    (paso === 3 && !!fecha && !!hora)

  async function confirmar(cliente: ClienteData) {
    if (!servicio || !barbero || !fecha || !hora) return
    setEnviando(true)
    setError(null)
    try {
      const nueva = await crearCita({
        servicioId: servicio.id,
        barberoId: barbero.id,
        barbero,
        inicio: construirInicio(fecha, hora),
        contactoNombre: cliente.nombre,
        contactoCelular: cliente.celular,
      })
      registrarCita(nueva)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'No se pudo registrar la reserva.')
    } finally {
      setEnviando(false)
    }
  }

  const enc = ENCABEZADOS[paso]
  const subtitulo =
    paso === 2 && servicio
      ? `Todos son especialistas en ${servicio.nombre.toLowerCase()}`
      : paso === 3 && barbero
        ? `Disponibilidad de ${barbero.nombre}`
        : enc.subtitulo

  return (
    <section className="overflow-hidden rounded-2xl border border-[#101820]/12 bg-[#FAFAF8] shadow-[0_18px_40px_-22px_rgb(16_24_32_/_45%)] dark:border-[#F7F1E8]/12 dark:bg-[#16202B]">
      {/* Barra de progreso del puesto: de rojo a azul barbero */}
      <div
        aria-hidden="true"
        className="h-1 w-full bg-[#101820]/10 dark:bg-[#F7F1E8]/10"
      >
        <div
          className="h-full bg-gradient-to-r from-[#B3263B] via-[#C93A4F] to-[#174A7E] transition-all duration-300"
          style={{ width: `${(paso / PASOS.length) * 100}%` }}
        />
      </div>

      <ol
        className="flex items-start justify-between border-b border-dashed border-[#101820]/15 px-4 py-5 sm:px-6 dark:border-[#F7F1E8]/15"
        aria-label="Progreso de la reserva"
      >
        {PASOS.map((p, i) => {
          const hecho = p.n < paso
          const actual = p.n === paso
          return (
            <li
              key={p.n}
              aria-current={actual ? 'step' : undefined}
              className="relative flex flex-1 flex-col items-center gap-1.5"
            >
              {i > 0 && (
                <span
                  aria-hidden="true"
                  className={cn(
                    'absolute right-1/2 top-[18px] h-px w-full',
                    hecho || actual
                      ? 'bg-[#B3263B] dark:bg-[#E5283C]'
                      : 'bg-[#101820]/15 dark:bg-white/15',
                  )}
                />
              )}
              <span
                className={cn(
                  'relative z-10 flex size-9 items-center justify-center rounded-full text-xs font-bold ring-4 transition-colors',
                  hecho && 'bg-[#174A7E] text-[#F7F1E8] ring-[#174A7E]/15',
                  actual &&
                    'bg-[#B3263B] text-[#F7F1E8] ring-[#B3263B]/20 dark:bg-[#E5283C] dark:text-[#101820] dark:ring-[#E5283C]/20',
                  !hecho &&
                    !actual &&
                    'bg-[#101820]/8 text-[#101820]/45 ring-transparent dark:bg-[#F7F1E8]/10 dark:text-[#F7F1E8]/45',
                )}
              >
                {hecho ? <Check className="size-4" /> : p.n}
              </span>
              <span
                className={cn(
                  'text-[10px] font-semibold tracking-wider uppercase',
                  !actual && 'hidden sm:block',
                  actual
                    ? 'text-[#B3263B] dark:text-[#E5283C]'
                    : 'text-[#101820]/45 dark:text-[#F7F1E8]/45',
                )}
              >
                {p.titulo}
              </span>
            </li>
          )
        })}
      </ol>

      <div className="px-4 py-5 sm:px-6 sm:py-6">
        <header className="mb-5">
          <h2 className="font-[Barlow_Condensed] text-2xl font-bold tracking-wide text-[#101820] uppercase dark:text-[#F7F1E8]">
            {enc.titulo}
          </h2>
          <p className="text-sm text-[#101820]/60 dark:text-[#F7F1E8]/60">
            {subtitulo}
          </p>
        </header>

        {paso === 1 && <PasoServicio />}
        {paso === 2 && <PasoBarbero />}
        {paso === 3 && <PasoFechaHora />}
        {paso === 4 && (
          <PasoConfirmar error={error} enviando={enviando} onConfirmar={confirmar} />
        )}
      </div>

      <footer className="relative flex items-center justify-between gap-3 border-t border-dashed border-[#101820]/15 px-4 py-4 sm:px-6 dark:border-[#F7F1E8]/15">
        <button
          type="button"
          className={botonSecundario}
          onClick={atras}
          disabled={paso === 1 || enviando}
        >
          Atrás
        </button>
        <span className="absolute left-1/2 top-1/2 hidden -translate-x-1/2 -translate-y-1/2 whitespace-nowrap text-[11px] text-slate-400 dark:text-white/40 min-[380px]:block sm:text-xs">
          Paso {paso} de 4
        </span>
        {paso < 4 ? (
          <button
            type="button"
            className={botonPrimario}
            onClick={siguiente}
            disabled={!puedeContinuar}
          >
            Continuar <ArrowRight className="size-4" />
          </button>
        ) : (
          // Confirmar vive en el cuerpo del paso 4, lejos de «Continuar»: un doble
          // clic en «Continuar» no puede caer sobre él y agendar sin querer.
          <span aria-hidden="true" />
        )}
      </footer>
    </section>
  )
}
