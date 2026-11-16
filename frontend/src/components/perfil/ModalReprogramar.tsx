import { useRef, useState } from 'react'
import { cn } from '@/lib/utils'
import { proximosDiasLaborales } from '@/lib/diasLaborales'
import {
  listarFranjas,
  type CitaConfirmada,
  type FranjaHoraria,
} from '@/lib/reservaApi'
import { botonPrimario, botonSecundario } from '@/components/booking/wizard/estilos'
import { fechaLocal } from '@/components/booking/wizard/formato'
import { Modal } from './Modal'

const DIAS_A_OFRECER = 7

const fechaEnBarberia = new Intl.DateTimeFormat('en-CA', {
  timeZone: 'America/Bogota',
  year: 'numeric',
  month: '2-digit',
  day: '2-digit',
})

interface Props {
  cita: CitaConfirmada
  /** Debe lanzar un Error con el mensaje a mostrar si el backend rechaza el cambio. */
  onConfirmar: (fecha: string, hora: string) => Promise<void>
  onCerrar: () => void
}

export function ModalReprogramar({ cita, onConfirmar, onCerrar }: Props) {
  // Solo se ofrecen los días que el barbero atiende según su horario configurado.
  const [dias] = useState(() =>
    proximosDiasLaborales(
      fechaEnBarberia.format(new Date()),
      cita.barbero.diasLaborales,
      DIAS_A_OFRECER,
    ),
  )
  const [fecha, setFecha] = useState<string | null>(null)
  const [hora, setHora] = useState<string | null>(null)
  const [franjas, setFranjas] = useState<FranjaHoraria[]>([])
  const [cargando, setCargando] = useState(false)
  const [errorFranjas, setErrorFranjas] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [enviando, setEnviando] = useState(false)
  // Si el cliente cambia de día antes de que responda la consulta anterior,
  // esa respuesta tardía se descarta.
  const consultaActual = useRef(0)

  async function elegirDia(dia: string) {
    const consulta = ++consultaActual.current
    setFecha(dia)
    setHora(null)
    setFranjas([])
    setErrorFranjas(null)
    setCargando(true)
    try {
      const libres = await listarFranjas(
        cita.barbero.id,
        dia,
        cita.servicio.duracionMin,
      )
      if (consulta === consultaActual.current)
        setFranjas(libres.filter((f) => f.disponible))
    } catch (err) {
      if (consulta === consultaActual.current) {
        setErrorFranjas(
          err instanceof Error ? err.message : 'No se pudieron cargar los horarios.',
        )
      }
    } finally {
      if (consulta === consultaActual.current) setCargando(false)
    }
  }

  async function confirmar() {
    if (!fecha || !hora) return
    setEnviando(true)
    setError(null)
    try {
      await onConfirmar(fecha, hora)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error al reprogramar la cita.')
      setEnviando(false)
    }
  }

  const actual = fechaLocal(cita.inicio.slice(0, 10)).toLocaleDateString('es-CO', {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
  })

  return (
    <Modal
      titulo="Reprogramar cita"
      subtitulo={`${cita.servicio.nombre} con ${cita.barbero.nombre}`}
      onCerrar={onCerrar}
      bloqueado={enviando}
      ancho="lg"
    >
      <p className="mb-4 rounded-xl bg-slate-50 p-3 text-sm text-slate-600 dark:bg-white/5 dark:text-white/65">
        Ahora: <strong className="capitalize">{actual}</strong> ·{' '}
        {cita.inicio.slice(11, 16)}
      </p>

      <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-white/55">
        1. Elige el día
      </p>
      {dias.length === 0 ? (
        <p role="status" className="text-sm text-slate-500 dark:text-white/55">
          {cita.barbero.nombre} no tiene días de atención configurados.
        </p>
      ) : (
        <div className="grid grid-cols-4 gap-2 sm:grid-cols-7">
          {dias.map((d) => {
            const f = fechaLocal(d)
            const activo = fecha === d
            return (
              <button
                key={d}
                type="button"
                aria-pressed={activo}
                onClick={() => void elegirDia(d)}
                className={cn(
                  'rounded-xl border py-2 text-center transition-colors',
                  activo
                    ? 'border-[#0B1B3A] bg-[#0B1B3A] text-white dark:border-[#d7b36a] dark:bg-[#d7b36a] dark:text-[#0f1210]'
                    : 'border-slate-200 bg-white text-slate-700 hover:border-[#0B1B3A] dark:border-white/10 dark:bg-transparent dark:text-white/80 dark:hover:border-[#d7b36a]',
                )}
              >
                <span className="block text-[10px] uppercase opacity-70">
                  {f.toLocaleDateString('es-CO', { weekday: 'short' }).replace('.', '')}
                </span>
                <span className="block text-sm font-bold">
                  {f.getDate()}{' '}
                  <span className="text-[10px] font-medium">
                    {f.toLocaleDateString('es-CO', { month: 'short' }).replace('.', '')}
                  </span>
                </span>
              </button>
            )
          })}
        </div>
      )}

      <p className="mb-2 mt-5 text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-white/55">
        2. Elige la hora
      </p>
      {!fecha ? (
        <p className="text-sm text-slate-500 dark:text-white/55">
          Primero elige un día.
        </p>
      ) : cargando ? (
        <p className="text-sm text-slate-500 dark:text-white/55">Cargando horarios…</p>
      ) : errorFranjas ? (
        <p role="alert" className="text-sm text-[#E5283C] dark:text-red-300">
          {errorFranjas}
        </p>
      ) : franjas.length === 0 ? (
        <p className="text-sm text-slate-500 dark:text-white/55">
          No hay horarios disponibles este día. Prueba con otro.
        </p>
      ) : (
        <div className="grid grid-cols-3 gap-2 sm:grid-cols-4">
          {franjas.map((f) => (
            <button
              key={f.hora}
              type="button"
              aria-label={`Hora ${f.hora}`}
              aria-pressed={hora === f.hora}
              onClick={() => setHora(f.hora)}
              className={cn(
                'rounded-xl border py-2 text-sm font-semibold transition-colors',
                hora === f.hora
                  ? 'border-[#E5283C] bg-[#E5283C] text-white dark:border-[#d7b36a] dark:bg-[#d7b36a] dark:text-[#0f1210]'
                  : 'border-slate-200 bg-white text-slate-700 hover:border-[#E5283C] dark:border-white/10 dark:bg-transparent dark:text-white/80 dark:hover:border-[#d7b36a]',
              )}
            >
              {f.hora}
            </button>
          ))}
        </div>
      )}

      {error && (
        <p
          role="alert"
          className="mt-4 rounded-xl bg-[#FEF2F3] p-3 text-sm text-[#E5283C] dark:bg-red-400/10 dark:text-red-300"
        >
          {error}
        </p>
      )}

      <div className="mt-5 flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
        <button
          type="button"
          onClick={onCerrar}
          disabled={enviando}
          className={botonSecundario}
        >
          Volver
        </button>
        <button
          type="button"
          onClick={() => void confirmar()}
          disabled={!hora || enviando}
          className={botonPrimario}
        >
          {enviando ? 'Guardando…' : 'Confirmar cambio'}
        </button>
      </div>
    </Modal>
  )
}
