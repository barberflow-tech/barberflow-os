import { useEffect, useState } from 'react'
import { listarBarberosApi, type BarberoApi } from '@/lib/barberosApi'
import {
  guardarHorarioApi,
  HorarioConflictoError,
  obtenerHorarioApi,
  type CitaEnConflicto,
  type HorarioDia,
} from '@/lib/horariosApi'
import { AdminShell } from './AdminShell'

const botonDorado =
  'inline-flex items-center justify-center gap-2 rounded-full bg-brand px-5 py-2.5 text-sm font-semibold text-brand-fg transition hover:bg-brand-hover disabled:cursor-not-allowed disabled:opacity-50'
const botonTexto =
  'text-xs font-semibold text-brand underline-offset-4 transition hover:underline'
const campo =
  'w-full rounded-lg border border-app-fg/15 bg-app px-3 py-2 text-sm text-app-fg outline-none focus:border-brand'

const DIAS = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']

/** Turno que se ofrece al abrir un día cerrado, y descanso al añadirlo. */
const TURNO_INICIAL = { open_time: '09:00', close_time: '18:00' }
const DESCANSO_INICIAL = { break_start: '13:00', break_duration_minutes: 60 }

/** Un día de la semana en edición; `null` = el barbero no trabaja ese día. */
type DiaEditable = HorarioDia | null

const aMinutos = (hora: string) => {
  const [h, m] = hora.split(':').map(Number)
  return h * 60 + m
}

const formatoCita = new Intl.DateTimeFormat('es-CO', {
  timeZone: 'America/Bogota',
  weekday: 'long',
  day: 'numeric',
  month: 'long',
  hour: 'numeric',
  minute: '2-digit',
})

function semanaDesde(days: HorarioDia[]): DiaEditable[] {
  return DIAS.map((_, i) => days.find((d) => d.weekday === i) ?? null)
}

/** Primer problema de la semana, con el nombre del día, o `null` si es válida. */
function validar(semana: DiaEditable[]): string | null {
  if (semana.every((d) => d === null)) return 'Abre al menos un día de la semana.'
  for (let i = 0; i < semana.length; i++) {
    const d = semana[i]
    if (!d) continue
    if (
      !d.open_time ||
      !d.close_time ||
      aMinutos(d.close_time) <= aMinutos(d.open_time)
    ) {
      return `${DIAS[i]}: la hora de cierre debe ser posterior a la apertura.`
    }
    if (d.break_start !== null) {
      const inicio = d.break_start ? aMinutos(d.break_start) : NaN
      const fin = inicio + (d.break_duration_minutes ?? 0)
      if (
        !(d.break_duration_minutes && d.break_duration_minutes > 0) ||
        !(inicio >= aMinutos(d.open_time) && fin <= aMinutos(d.close_time))
      ) {
        return `${DIAS[i]}: el descanso debe quedar dentro del turno.`
      }
    }
  }
  return null
}

type Aviso =
  | { tipo: 'error'; texto: string; conflictos?: CitaEnConflicto[] }
  | { tipo: 'ok'; texto: string }

/** El admin define el turno y el descanso de cada día de un barbero. */
export function HorariosManager() {
  const [barberos, setBarberos] = useState<BarberoApi[]>([])
  const [barberoId, setBarberoId] = useState<number | null>(null)
  const [semana, setSemana] = useState<DiaEditable[]>(DIAS.map(() => null))
  const [cargando, setCargando] = useState(true)
  const [guardando, setGuardando] = useState(false)
  const [aviso, setAviso] = useState<Aviso | null>(null)

  useEffect(() => {
    let vigente = true
    listarBarberosApi()
      .then((lista) => {
        if (!vigente) return
        setBarberos(lista)
        setBarberoId(lista[0]?.id ?? null)
        if (lista.length === 0) setCargando(false)
      })
      .catch((e: unknown) => {
        if (!vigente) return
        setAviso({
          tipo: 'error',
          texto: e instanceof Error ? e.message : 'No se pudo cargar la información.',
        })
        setCargando(false)
      })
    return () => {
      vigente = false
    }
  }, [])

  useEffect(() => {
    if (barberoId === null) return
    let vigente = true
    obtenerHorarioApi(barberoId)
      .then((horario) => {
        if (vigente) setSemana(semanaDesde(horario.days))
      })
      .catch((e: unknown) => {
        if (!vigente) return
        setSemana(DIAS.map(() => null))
        setAviso({
          tipo: 'error',
          texto: e instanceof Error ? e.message : 'No se pudo cargar el horario.',
        })
      })
      .finally(() => {
        if (vigente) setCargando(false)
      })
    return () => {
      vigente = false
    }
  }, [barberoId])

  function cambiarDia(indice: number, cambios: Partial<HorarioDia> | null) {
    setAviso(null)
    setSemana((previa) =>
      previa.map((d, i) =>
        i !== indice
          ? d
          : cambios === null
            ? null
            : { ...(d as HorarioDia), ...cambios },
      ),
    )
  }

  function abrirDia(indice: number) {
    setAviso(null)
    setSemana((previa) =>
      previa.map((d, i) =>
        i === indice
          ? {
              weekday: i,
              ...TURNO_INICIAL,
              break_start: null,
              break_duration_minutes: null,
            }
          : d,
      ),
    )
  }

  async function guardar() {
    if (barberoId === null) return
    const problema = validar(semana)
    if (problema) {
      setAviso({ tipo: 'error', texto: problema })
      return
    }
    setGuardando(true)
    setAviso(null)
    try {
      const guardado = await guardarHorarioApi(
        barberoId,
        semana.filter((d): d is HorarioDia => d !== null),
      )
      setSemana(semanaDesde(guardado.days))
      setAviso({ tipo: 'ok', texto: 'Horario guardado' })
    } catch (e) {
      setAviso({
        tipo: 'error',
        texto: e instanceof Error ? e.message : 'No se pudo guardar el horario.',
        conflictos: e instanceof HorarioConflictoError ? e.conflictos : undefined,
      })
    } finally {
      setGuardando(false)
    }
  }

  return (
    <AdminShell>
      <p className="mb-4 flex items-center gap-3 text-xs font-semibold tracking-[0.22em] text-brand uppercase">
        <span className="h-px w-8 bg-brand" />
        Disponibilidad
      </p>
      <h1 className="font-['Playfair_Display',serif] text-4xl leading-tight sm:text-5xl">
        Horarios de los barberos
      </h1>
      <p className="mt-3 max-w-xl text-app-fg/60">
        Define el turno y el descanso de cada día. Los clientes solo podrán reservar
        franjas dentro del turno.
      </p>

      {barberos.length > 0 && (
        <div className="mt-10 max-w-xs">
          <label
            htmlFor="barbero-horario"
            className="mb-2 block text-xs text-app-fg/60"
          >
            Barbero
          </label>
          <select
            id="barbero-horario"
            value={barberoId ?? ''}
            onChange={(e) => {
              setCargando(true)
              setAviso(null)
              setBarberoId(Number(e.target.value))
            }}
            className={campo}
          >
            {barberos.map((b) => (
              <option key={b.id} value={b.id}>
                {b.name}
              </option>
            ))}
          </select>
        </div>
      )}

      {cargando && (
        <p role="status" className="mt-12 text-app-fg/60">
          Cargando horario…
        </p>
      )}
      {!cargando && barberos.length === 0 && !aviso && (
        <p className="mt-12 text-app-fg/60">Aún no hay barberos registrados.</p>
      )}

      {aviso?.tipo === 'error' && (
        <div role="alert" className="mt-8 text-sm text-red-400">
          <p>{aviso.texto}</p>
          {aviso.conflictos && aviso.conflictos.length > 0 && (
            <ul className="mt-2 list-disc space-y-1 pl-5">
              {aviso.conflictos.map((c) => (
                <li key={c.appointment}>
                  Cita #{c.appointment} · {formatoCita.format(new Date(c.start_at))}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      {!cargando && barberoId !== null && (
        <>
          <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {semana.map((d, i) => (
              <section
                key={DIAS[i]}
                role="group"
                aria-label={DIAS[i]}
                className="rounded-2xl border border-app-fg/10 bg-app-fg/[0.03] p-5"
              >
                <div className="flex items-center justify-between">
                  <h2 className="font-['Playfair_Display',serif] text-xl">{DIAS[i]}</h2>
                  <span
                    className={
                      d
                        ? 'text-[0.65rem] font-semibold tracking-[0.18em] text-brand uppercase'
                        : 'text-[0.65rem] font-semibold tracking-[0.18em] text-app-fg/45 uppercase'
                    }
                  >
                    {d ? 'Abierto' : 'Cerrado'}
                  </span>
                </div>

                {d ? (
                  <div className="mt-4 space-y-3">
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <label
                          htmlFor={`apertura-${i}`}
                          className="mb-1 block text-xs text-app-fg/60"
                        >
                          Apertura
                        </label>
                        <input
                          id={`apertura-${i}`}
                          type="time"
                          value={d.open_time}
                          onChange={(e) => cambiarDia(i, { open_time: e.target.value })}
                          className={campo}
                        />
                      </div>
                      <div>
                        <label
                          htmlFor={`cierre-${i}`}
                          className="mb-1 block text-xs text-app-fg/60"
                        >
                          Cierre
                        </label>
                        <input
                          id={`cierre-${i}`}
                          type="time"
                          value={d.close_time}
                          onChange={(e) =>
                            cambiarDia(i, { close_time: e.target.value })
                          }
                          className={campo}
                        />
                      </div>
                    </div>

                    {d.break_start !== null ? (
                      <div className="grid grid-cols-2 gap-3">
                        <div>
                          <label
                            htmlFor={`descanso-${i}`}
                            className="mb-1 block text-xs text-app-fg/60"
                          >
                            Inicio del descanso
                          </label>
                          <input
                            id={`descanso-${i}`}
                            type="time"
                            value={d.break_start}
                            onChange={(e) =>
                              cambiarDia(i, { break_start: e.target.value })
                            }
                            className={campo}
                          />
                        </div>
                        <div>
                          <label
                            htmlFor={`duracion-${i}`}
                            className="mb-1 block text-xs text-app-fg/60"
                          >
                            Duración del descanso (min)
                          </label>
                          <input
                            id={`duracion-${i}`}
                            type="number"
                            min={5}
                            step={5}
                            value={d.break_duration_minutes ?? ''}
                            onChange={(e) =>
                              cambiarDia(i, {
                                break_duration_minutes:
                                  e.target.value === '' ? null : Number(e.target.value),
                              })
                            }
                            className={campo}
                          />
                        </div>
                      </div>
                    ) : null}

                    <div className="flex flex-wrap gap-4 pt-1">
                      {d.break_start !== null ? (
                        <button
                          type="button"
                          className={botonTexto}
                          onClick={() =>
                            cambiarDia(i, {
                              break_start: null,
                              break_duration_minutes: null,
                            })
                          }
                        >
                          Quitar descanso
                        </button>
                      ) : (
                        <button
                          type="button"
                          className={botonTexto}
                          onClick={() => cambiarDia(i, DESCANSO_INICIAL)}
                        >
                          Añadir descanso
                        </button>
                      )}
                      <button
                        type="button"
                        className={botonTexto}
                        onClick={() => cambiarDia(i, null)}
                      >
                        Marcar cerrado
                      </button>
                    </div>
                  </div>
                ) : (
                  <div className="mt-4">
                    <p className="text-sm text-app-fg/50">Sin franjas configuradas.</p>
                    <button
                      type="button"
                      className={`${botonTexto} mt-3`}
                      onClick={() => abrirDia(i)}
                    >
                      Abrir día
                    </button>
                  </div>
                )}
              </section>
            ))}
          </div>

          <div className="mt-8 flex flex-wrap items-center gap-4">
            <button
              type="button"
              className={botonDorado}
              disabled={guardando}
              onClick={() => void guardar()}
            >
              {guardando ? 'Guardando…' : 'Guardar horario'}
            </button>
            {aviso?.tipo === 'ok' && (
              <p role="status" className="text-sm text-brand">
                {aviso.texto}
              </p>
            )}
          </div>
        </>
      )}
    </AdminShell>
  )
}
