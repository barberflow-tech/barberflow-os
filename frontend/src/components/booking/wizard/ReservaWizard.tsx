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
    <section className="overflow-hidden rounded-2xl border border-slate-200 dark:border-white/10 bg-white dark:bg-[#151915] shadow-sm">
      <ol
        className="flex items-start justify-between px-4 py-5 sm:px-6"
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
                    'absolute right-1/2 top-4 h-px w-full',
                    hecho || actual
                      ? 'bg-emerald-500'
                      : 'bg-slate-200 dark:bg-white/15',
                  )}
                />
              )}
              <span
                className={cn(
                  'relative z-10 flex size-8 items-center justify-center rounded-full text-xs font-bold',
                  hecho && 'bg-emerald-500 text-white',
                  actual &&
                    'bg-[#E5283C] dark:bg-[#d7b36a] text-white dark:text-[#111411] ring-4 ring-[#E5283C]/15',
                  !hecho &&
                    !actual &&
                    'bg-slate-100 dark:bg-white/10 text-slate-400 dark:text-white/40',
                )}
              >
                {hecho ? <Check className="size-4" /> : p.n}
              </span>
              <span
                className={cn(
                  'text-[10px] font-semibold uppercase tracking-wider',
                  !actual && 'hidden sm:block',
                  actual
                    ? 'text-[#0B1B3A] dark:text-[#f4f1e9]'
                    : 'text-slate-400 dark:text-white/40',
                )}
              >
                {p.titulo}
              </span>
            </li>
          )
        })}
      </ol>

      <div className="border-t border-slate-100 dark:border-white/5 px-4 py-5 sm:px-6 sm:py-6">
        <header className="mb-5">
          <h2 className="text-lg font-bold text-[#0B1B3A] dark:text-[#f4f1e9]">
            {enc.titulo}
          </h2>
          <p className="text-sm text-slate-500 dark:text-white/55">{subtitulo}</p>
        </header>

        {paso === 1 && <PasoServicio />}
        {paso === 2 && <PasoBarbero />}
        {paso === 3 && <PasoFechaHora />}
        {paso === 4 && <PasoConfirmar error={error} onConfirmar={confirmar} />}
      </div>

      <footer className="flex items-center justify-between gap-3 border-t border-slate-100 dark:border-white/5 px-4 py-4 sm:px-6">
        <button
          type="button"
          className={botonSecundario}
          onClick={atras}
          disabled={paso === 1 || enviando}
        >
          Atrás
        </button>
        <span className="hidden whitespace-nowrap text-[11px] text-slate-400 dark:text-white/40 min-[380px]:block sm:text-xs">
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
          <button
            type="submit"
            form="form-confirmar"
            className={botonPrimario}
            disabled={enviando}
          >
            {enviando ? (
              'Confirmando…'
            ) : (
              <span className="whitespace-nowrap">
                Confirmar <span className="hidden min-[380px]:inline">reserva</span>
              </span>
            )}
            {!enviando && <ArrowRight className="size-4" />}
          </button>
        )}
      </footer>
    </section>
  )
}
