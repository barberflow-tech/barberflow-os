import React, { useEffect, useMemo, useRef, useState } from 'react'
import { useCitasStore } from '@/stores/useCitasStore'
import { useAuthStore } from '@/stores/useAuthStore'
import {
  listarFranjas,
  type CitaConfirmada,
  type FranjaHoraria,
} from '@/lib/reservaApi'

const ZONA_BARBERIA = 'America/Bogota'
const DIAS_A_OFRECER = 7

const fechaEnBarberia = new Intl.DateTimeFormat('en-CA', {
  timeZone: ZONA_BARBERIA,
  year: 'numeric',
  month: '2-digit',
  day: '2-digit',
})

interface DiaOfrecido {
  fecha: string
  label: string
  diaNombre: string
}

/** Hoy y los próximos días en la hora de la barbería (Colombia no tiene horario de verano). */
function diasProximos(cantidad = DIAS_A_OFRECER): DiaOfrecido[] {
  const hoy = fechaEnBarberia.format(new Date())
  const base = Date.parse(`${hoy}T12:00:00Z`)
  return Array.from({ length: cantidad }, (_, i) => {
    const d = new Date(base + i * 24 * 60 * 60 * 1000)
    const diaSemana = d
      .toLocaleDateString('es-CO', { weekday: 'short', timeZone: 'UTC' })
      .replace('.', '')
    const numero = String(d.getUTCDate()).padStart(2, '0')
    return {
      fecha: d.toISOString().slice(0, 10),
      label: i === 0 ? 'Hoy' : i === 1 ? 'Mañana' : diaSemana,
      diaNombre: `${diaSemana} ${numero}`,
    }
  })
}

/** "14:30" -> "02:30 PM" */
function aHora12(hora: string): string {
  const [h, m] = hora.split(':').map(Number)
  const sufijo = h < 12 ? 'AM' : 'PM'
  return `${String(h % 12 || 12).padStart(2, '0')}:${String(m).padStart(2, '0')} ${sufijo}`
}

export function PerfilPage() {
  const { user } = useAuthStore()
  const { citas, isLoading, error, fetchMisCitas, cancelarCita, reprogramarCita } =
    useCitasStore()

  const [citaAReprogramar, setCitaAReprogramar] = useState<CitaConfirmada | null>(null)
  const [citaACancelar, setCitaACancelar] = useState<CitaConfirmada | null>(null)
  const [mensajeAlerta, setMensajeAlerta] = useState<string | null>(null)

  const dias = useMemo(() => diasProximos(), [])
  const [fechaSeleccionada, setFechaSeleccionada] = useState<string>(dias[0].fecha)
  const [horaSeleccionada, setHoraSeleccionada] = useState<string>('')
  const [modalError, setModalError] = useState<string | null>(null)
  const [franjas, setFranjas] = useState<FranjaHoraria[]>([])
  const [cargandoFranjas, setCargandoFranjas] = useState(false)
  const [errorFranjas, setErrorFranjas] = useState<string | null>(null)
  // Cada consulta lleva un número: si el cliente cambia de día antes de que
  // responda la anterior, esa respuesta tardía se descarta.
  const consultaActual = useRef(0)

  useEffect(() => {
    fetchMisCitas()
  }, [fetchMisCitas])

  // HU-03: reprogramar exige MÁS de 12 horas de antelación (12 justas no basta).
  // Cancelar siempre se permite; con 12 h o menos queda registrada como tardía.
  const cumpleAntelacion = (fechaInicio: string): boolean => {
    const ahora = new Date().getTime()
    const tiempoCita = new Date(fechaInicio).getTime()
    const horasRestantes = (tiempoCita - ahora) / (1000 * 60 * 60)
    return horasRestantes > 12
  }

  /** Pide al backend los horarios libres del barbero de la cita para ese día. */
  const cargarFranjas = async (cita: CitaConfirmada, fecha: string) => {
    const consulta = ++consultaActual.current
    setCargandoFranjas(true)
    setErrorFranjas(null)
    setFranjas([])
    try {
      const libres = await listarFranjas(
        cita.barbero.id,
        fecha,
        cita.servicio.duracionMin,
      )
      if (consulta === consultaActual.current) {
        setFranjas(libres.filter((f) => f.disponible))
      }
    } catch (err: unknown) {
      if (consulta === consultaActual.current) {
        setErrorFranjas(
          err instanceof Error ? err.message : 'No se pudieron cargar los horarios.',
        )
      }
    } finally {
      if (consulta === consultaActual.current) setCargandoFranjas(false)
    }
  }

  const handleSolicitarCancelar = (cita: CitaConfirmada) => {
    setCitaACancelar(cita)
  }

  const handleSolicitarReprogramar = (cita: CitaConfirmada) => {
    if (!cumpleAntelacion(cita.inicio)) {
      setMensajeAlerta(
        'No se puede reprogramar la cita con menos de 12 horas de antelación.',
      )
      return
    }
    setCitaAReprogramar(cita)
    setHoraSeleccionada('')
    setModalError(null)
    setFechaSeleccionada(dias[0].fecha)
    void cargarFranjas(cita, dias[0].fecha)
  }

  const confirmCancelar = async () => {
    if (!citaACancelar) return
    try {
      const { tardia } = await cancelarCita(citaACancelar.id)
      setCitaACancelar(null)
      if (tardia) {
        setMensajeAlerta(
          'Tu cita fue cancelada. Como faltaban 12 horas o menos, quedó registrada como cancelación tardía.',
        )
      }
    } catch (err: unknown) {
      const mensaje = err instanceof Error ? err.message : 'Error al cancelar la cita.'
      setMensajeAlerta(mensaje)
    }
  }

  const handleReprogramarSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!citaAReprogramar || !fechaSeleccionada || !horaSeleccionada) {
      setModalError('Por favor selecciona una fecha y una hora válida.')
      return
    }

    // El backend exige ISO 8601 con zona; las franjas son hora de Colombia.
    const nuevoHorarioISO = `${fechaSeleccionada}T${horaSeleccionada}:00-05:00`

    if (!cumpleAntelacion(citaAReprogramar.inicio)) {
      setModalError(
        'No se puede reprogramar la cita con menos de 12 horas de antelación.',
      )
      return
    }

    try {
      await reprogramarCita(citaAReprogramar.id, nuevoHorarioISO)
      setCitaAReprogramar(null)
      setHoraSeleccionada('')
      setModalError(null)
    } catch (err: unknown) {
      const mensaje =
        err instanceof Error ? err.message : 'Error al reprogramar la cita.'
      setModalError(mensaje)
    }
  }

  return (
    <div className="w-full max-w-6xl mx-auto p-6 space-y-8 bg-slate-50 dark:bg-gray-950 min-h-screen">
      {/* Cabecera del Perfil */}
      <div className="bg-white dark:bg-gray-900 p-6 rounded-3xl shadow-sm border border-slate-200 dark:border-gray-800 flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-black text-slate-900 dark:text-white uppercase tracking-tight">
            Mi Perfil y Citas
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            Bienvenido, {user?.email ?? 'Cliente'}. Gestiona tus citas activas.
          </p>
        </div>
        <div className="bg-slate-100 dark:bg-gray-800 px-4 py-2 rounded-xl text-xs font-bold text-slate-700 dark:text-slate-300">
          Rol: Cliente
        </div>
      </div>

      {/* Listado de Citas Activas */}
      <div className="bg-white dark:bg-gray-900 p-6 rounded-3xl shadow-sm border border-slate-200 dark:border-gray-800 space-y-4">
        <h2 className="text-lg font-black text-slate-900 dark:text-white">
          Mis Citas Activas
        </h2>

        {isLoading && <p className="text-xs text-slate-400">Cargando citas...</p>}
        {error && <p className="text-xs text-red-500">{error}</p>}

        {!isLoading && citas.length === 0 && (
          <p className="text-xs text-slate-400">
            No tienes citas programadas actualmente.
          </p>
        )}

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {citas.map((cita) => (
            <div
              key={cita.id}
              className="p-5 rounded-3xl border border-slate-200 dark:border-gray-800 bg-slate-50 dark:bg-gray-900/60 shadow-sm flex flex-col justify-between space-y-4"
            >
              <div>
                <div className="flex justify-between items-start gap-2">
                  <h3 className="text-base font-extrabold text-slate-900 dark:text-white">
                    {cita.servicio.nombre}
                  </h3>
                  <span className="text-[10px] font-black px-2.5 py-1 rounded-lg bg-amber-100 text-amber-700 dark:bg-amber-950/60 dark:text-amber-400 uppercase tracking-wider">
                    {cita.estado}
                  </span>
                </div>
                <p className="text-xs text-slate-500 mt-1">
                  Barbero:{' '}
                  <span className="font-semibold text-slate-700 dark:text-slate-300">
                    {cita.barbero.nombre}
                  </span>
                </p>
                <div className="flex items-center gap-2 mt-3 text-xs font-semibold text-slate-600 dark:text-slate-400 bg-white dark:bg-gray-800/80 p-2.5 rounded-xl border border-slate-200/60 dark:border-gray-700/60 w-fit">
                  <span>📅</span>
                  <span>
                    {new Date(cita.inicio).toLocaleString('es-CO', {
                      dateStyle: 'medium',
                      timeStyle: 'short',
                    })}
                  </span>
                </div>
              </div>

              <div className="flex items-center justify-between pt-3 border-t border-slate-200 dark:border-gray-800">
                <span className="text-base font-black text-slate-900 dark:text-white">
                  ${cita.total.toLocaleString('es-CO')}
                </span>

                <div className="flex gap-2">
                  <button
                    onClick={() => handleSolicitarReprogramar(cita)}
                    className="px-4 py-2 text-xs font-bold rounded-xl bg-slate-900 text-white dark:bg-white dark:text-slate-900 hover:opacity-90 transition-all cursor-pointer shadow-sm"
                  >
                    Reprogramar
                  </button>
                  <button
                    onClick={() => handleSolicitarCancelar(cita)}
                    className="px-4 py-2 text-xs font-bold rounded-xl bg-red-100 text-red-600 dark:bg-red-950/50 dark:text-red-400 hover:bg-red-200 dark:hover:bg-red-900/50 transition-all cursor-pointer"
                  >
                    Cancelar
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* MODAL 1: Advertencia de Antelación */}
      {mensajeAlerta && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <div className="w-full max-w-md rounded-3xl bg-white dark:bg-gray-900 p-6 shadow-2xl border border-slate-200 dark:border-gray-800 space-y-4 text-center">
            <div className="w-14 h-14 mx-auto flex items-center justify-center rounded-full bg-amber-100 dark:bg-amber-950/50 text-amber-600 dark:text-amber-400">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                className="w-7 h-7"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z" />
                <line x1="12" y1="9" x2="12" y2="13" />
                <line x1="12" y1="17" x2="12.01" y2="17" />
              </svg>
            </div>
            <h3 className="text-lg font-black text-slate-900 dark:text-white">
              Restricción de Horario
            </h3>
            <p className="text-xs text-slate-500 dark:text-slate-400 leading-relaxed">
              {mensajeAlerta}
            </p>
            <button
              onClick={() => setMensajeAlerta(null)}
              className="w-full py-3 text-xs font-bold rounded-xl bg-slate-900 text-white dark:bg-white dark:text-slate-900 shadow-sm hover:opacity-90 transition-all cursor-pointer"
            >
              Entendido
            </button>
          </div>
        </div>
      )}

      {/* MODAL 2: Confirmación de Cancelación */}
      {citaACancelar && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <div className="w-full max-w-md rounded-3xl bg-white dark:bg-gray-900 p-6 shadow-2xl border border-slate-200 dark:border-gray-800 space-y-5 text-center">
            <div className="w-14 h-14 mx-auto flex items-center justify-center rounded-full bg-red-100 dark:bg-red-950/50 text-red-600 dark:text-red-400">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                className="w-7 h-7"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="M3 6h18" />
                <path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6" />
                <path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2" />
              </svg>
            </div>
            <div>
              <h3 className="text-lg font-black text-slate-900 dark:text-white">
                ¿Cancelar esta cita?
              </h3>
              <p className="text-xs text-slate-500 dark:text-slate-400 mt-2">
                Estás a punto de cancelar tu cita para{' '}
                <span className="font-bold text-slate-800 dark:text-slate-200">
                  {citaACancelar.servicio.nombre}
                </span>{' '}
                con {citaACancelar.barbero.nombre}. Esta acción no se puede deshacer.
              </p>
              {!cumpleAntelacion(citaACancelar.inicio) && (
                <p className="text-xs font-semibold text-amber-600 dark:text-amber-400 mt-2">
                  Faltan 12 horas o menos: la cancelación se registrará como tardía.
                </p>
              )}
            </div>

            <div className="flex gap-3 pt-2">
              <button
                type="button"
                onClick={() => setCitaACancelar(null)}
                className="flex-1 py-3 text-xs font-bold rounded-xl bg-slate-100 dark:bg-gray-800 text-slate-600 dark:text-slate-300 hover:bg-slate-200 transition-all cursor-pointer"
              >
                Volver
              </button>
              <button
                type="button"
                onClick={confirmCancelar}
                className="flex-1 py-3 text-xs font-bold rounded-xl bg-red-600 text-white hover:bg-red-700 shadow-sm transition-all cursor-pointer"
              >
                Sí, cancelar
              </button>
            </div>
          </div>
        </div>
      )}

      {/* MODAL 3: Reprogramar Cita */}
      {citaAReprogramar && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <div className="bg-white dark:bg-gray-900 rounded-3xl max-w-lg w-full p-6 shadow-2xl border border-slate-200 dark:border-gray-800 space-y-5 max-h-[90vh] overflow-y-auto">
            <div className="flex justify-between items-start">
              <div>
                <h2 className="text-lg font-black text-slate-900 dark:text-white">
                  Reprogramar Cita
                </h2>
                <p className="text-xs text-slate-500 mt-0.5">
                  Servicio:{' '}
                  <span className="font-bold text-slate-800 dark:text-slate-200">
                    {citaAReprogramar.servicio.nombre}
                  </span>{' '}
                  ({citaAReprogramar.barbero.nombre})
                </p>
              </div>
              <button
                onClick={() => {
                  setCitaAReprogramar(null)
                  setModalError(null)
                  setHoraSeleccionada('')
                }}
                className="w-8 h-8 rounded-full bg-slate-100 dark:bg-gray-800 flex items-center justify-center text-slate-400 hover:text-slate-600 dark:hover:text-white transition-colors cursor-pointer"
              >
                ✕
              </button>
            </div>

            {/* Resumen del Horario Actual */}
            <div className="p-3.5 rounded-2xl bg-amber-50/60 dark:bg-amber-950/20 border border-amber-200/80 dark:border-amber-900/50 text-xs space-y-1">
              <span className="text-[10px] uppercase font-bold text-amber-700 dark:text-amber-400 tracking-wider block">
                Cita Agendada Actualmente
              </span>
              <p className="font-bold text-slate-800 dark:text-slate-200 flex items-center gap-2">
                <span>📅</span>
                {new Date(citaAReprogramar.inicio).toLocaleString('es-CO', {
                  dateStyle: 'full',
                  timeStyle: 'short',
                })}
              </p>
            </div>

            {modalError && (
              <div className="p-3 rounded-xl bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-900/50 text-xs font-semibold text-red-600 dark:text-red-400">
                {modalError}
              </div>
            )}

            <form onSubmit={handleReprogramarSubmit} className="space-y-5">
              {/* PASO 1: Selector de Día */}
              <div>
                <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-2">
                  1. Selecciona el día
                </label>
                <div className="grid grid-cols-4 sm:grid-cols-7 gap-1.5">
                  {dias.map((d) => {
                    const esSeleccionado = fechaSeleccionada === d.fecha
                    return (
                      <button
                        key={d.fecha}
                        type="button"
                        onClick={() => {
                          setFechaSeleccionada(d.fecha)
                          setHoraSeleccionada('')
                          void cargarFranjas(citaAReprogramar, d.fecha)
                        }}
                        className={`p-2 rounded-xl text-center border text-xs transition-all cursor-pointer ${
                          esSeleccionado
                            ? 'bg-slate-900 text-white dark:bg-white dark:text-slate-900 font-extrabold border-slate-900 dark:border-white shadow-sm'
                            : 'bg-slate-50 dark:bg-gray-800 text-slate-600 dark:text-slate-300 border-slate-200 dark:border-gray-700 hover:bg-slate-100 dark:hover:bg-gray-750'
                        }`}
                      >
                        <span className="block text-[10px] opacity-75 font-normal">
                          {d.label}
                        </span>
                        <span className="block font-bold mt-0.5">{d.diaNombre}</span>
                      </button>
                    )
                  })}
                </div>
              </div>

              {/* PASO 2: Selector de Franja Horaria */}
              <div>
                <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-2">
                  2. Selecciona la hora disponible
                </label>

                {cargandoFranjas && (
                  <p className="text-xs text-slate-500">Cargando horarios…</p>
                )}
                {errorFranjas && (
                  <p className="text-xs font-semibold text-red-600 dark:text-red-400">
                    {errorFranjas}
                  </p>
                )}
                {!cargandoFranjas && !errorFranjas && franjas.length === 0 && (
                  <p className="text-xs text-slate-500">
                    No hay horarios disponibles este día. Prueba con otro.
                  </p>
                )}
                {franjas.length > 0 && (
                  <div className="grid grid-cols-3 sm:grid-cols-4 gap-2">
                    {franjas.map((f) => {
                      const esHoraSeleccionada = horaSeleccionada === f.hora
                      return (
                        <button
                          key={f.hora}
                          type="button"
                          onClick={() => setHoraSeleccionada(f.hora)}
                          className={`py-2.5 px-3 rounded-xl text-xs font-bold border transition-all cursor-pointer text-center ${
                            esHoraSeleccionada
                              ? 'bg-emerald-600 text-white border-emerald-600 shadow-sm'
                              : 'bg-slate-50 dark:bg-gray-800 text-slate-700 dark:text-slate-200 border-slate-200 dark:border-gray-700 hover:border-emerald-500'
                          }`}
                        >
                          {aHora12(f.hora)}
                        </button>
                      )
                    })}
                  </div>
                )}
              </div>

              {/* Confirmación visual previa */}
              {horaSeleccionada && (
                <div className="p-3.5 rounded-2xl bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-900/60 text-xs text-emerald-900 dark:text-emerald-300 flex items-center gap-3">
                  <span className="text-xl">✨</span>
                  <div>
                    <span className="font-extrabold block text-[11px] uppercase tracking-wider text-emerald-700 dark:text-emerald-400">
                      Nuevo horario seleccionado:
                    </span>
                    <span className="font-bold">
                      {fechaSeleccionada} — {aHora12(horaSeleccionada)}
                    </span>
                  </div>
                </div>
              )}

              <div className="flex justify-end gap-3 pt-3 border-t border-slate-100 dark:border-gray-800">
                <button
                  type="button"
                  onClick={() => {
                    setCitaAReprogramar(null)
                    setModalError(null)
                    setHoraSeleccionada('')
                  }}
                  className="px-4 py-2.5 text-xs font-bold rounded-xl bg-slate-100 dark:bg-gray-800 text-slate-600 dark:text-slate-300 hover:bg-slate-200 transition-all cursor-pointer"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  disabled={!horaSeleccionada}
                  className={`px-5 py-2.5 text-xs font-bold rounded-xl transition-all cursor-pointer ${
                    horaSeleccionada
                      ? 'bg-slate-900 text-white dark:bg-white dark:text-slate-900 shadow-md hover:opacity-90'
                      : 'bg-slate-200 text-slate-400 dark:bg-gray-800 dark:text-slate-600 cursor-not-allowed'
                  }`}
                >
                  Confirmar Cambio
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
