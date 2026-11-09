import React, { useEffect, useState } from 'react'
import { useCitasStore } from '@/stores/useCitasStore'
import { useAuthStore } from '@/stores/useAuthStore'
import type { CitaConfirmada } from '@/lib/reservaApi'

// Días de prueba para el selector rápido del modal
const DIAS_DISPONIBLES = [
  { label: 'Hoy', fecha: '2026-11-09', diaNombre: 'Lun 09' },
  { label: 'Mañana', fecha: '2026-11-10', diaNombre: 'Mar 10' },
  { label: 'Miércoles', fecha: '2026-11-11', diaNombre: 'Mié 11' },
  { label: 'Jueves', fecha: '2026-11-12', diaNombre: 'Jue 12' },
  { label: 'Viernes', fecha: '2026-11-13', diaNombre: 'Vie 13' },
]

// Horarios disponibles (Mañana / Tarde)
const FRANJAS_HORARIAS = {
  manana: [
    { id: 'h1', hora: '09:00', label: '09:00 AM' },
    { id: 'h2', hora: '10:00', label: '10:00 AM' },
    { id: 'h3', hora: '11:00', label: '11:00 AM' },
  ],
  tarde: [
    { id: 'h4', hora: '14:00', label: '02:00 PM' },
    { id: 'h5', hora: '15:00', label: '03:00 PM' },
    { id: 'h6', hora: '16:00', label: '04:00 PM' },
    { id: 'h7', hora: '17:00', label: '05:00 PM' },
  ],
}

export function PerfilPage() {
  const { user } = useAuthStore()
  const { citas, isLoading, error, fetchMisCitas, cancelarCita, reprogramarCita } =
    useCitasStore()

  const [citaAReprogramar, setCitaAReprogramar] = useState<CitaConfirmada | null>(null)
  const [citaACancelar, setCitaACancelar] = useState<CitaConfirmada | null>(null)
  const [mensajeAlerta, setMensajeAlerta] = useState<string | null>(null)

  const [fechaSeleccionada, setFechaSeleccionada] = useState<string>(
    DIAS_DISPONIBLES[1].fecha,
  )
  const [horaSeleccionada, setHoraSeleccionada] = useState<string>('')
  const [modalError, setModalError] = useState<string | null>(null)

  useEffect(() => {
    fetchMisCitas()
  }, [fetchMisCitas])

  // Regla de negocio: mínimo 12 horas de antelación
  const cumpleAntelacion = (fechaInicio: string): boolean => {
    const ahora = new Date().getTime()
    const tiempoCita = new Date(fechaInicio).getTime()
    const horasRestantes = (tiempoCita - ahora) / (1000 * 60 * 60)
    return horasRestantes >= 12
  }

  const handleSolicitarCancelar = (cita: CitaConfirmada) => {
    if (!cumpleAntelacion(cita.inicio)) {
      setMensajeAlerta(
        'No se puede cancelar la cita con menos de 12 horas de antelación.',
      )
      return
    }
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
  }

  const confirmCancelar = async () => {
    if (!citaACancelar) return
    try {
      await cancelarCita(citaACancelar.id)
      setCitaACancelar(null)
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

    const nuevoHorarioISO = `${fechaSeleccionada}T${horaSeleccionada}:00`

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
            Bienvenido, {user?.nombre ?? 'Cliente'}. Gestiona tus citas activas.
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
                <div className="grid grid-cols-5 gap-1.5">
                  {DIAS_DISPONIBLES.map((d) => {
                    const esSeleccionado = fechaSeleccionada === d.fecha
                    return (
                      <button
                        key={d.fecha}
                        type="button"
                        onClick={() => setFechaSeleccionada(d.fecha)}
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

                <div className="space-y-3">
                  {/* Mañana */}
                  <div>
                    <span className="text-[10px] font-bold uppercase text-slate-400 tracking-wider block mb-1.5">
                      Mañana
                    </span>
                    <div className="grid grid-cols-3 gap-2">
                      {FRANJAS_HORARIAS.manana.map((h) => {
                        const esHoraSeleccionada = horaSeleccionada === h.hora
                        return (
                          <button
                            key={h.id}
                            type="button"
                            onClick={() => setHoraSeleccionada(h.hora)}
                            className={`py-2.5 px-3 rounded-xl text-xs font-bold border transition-all cursor-pointer text-center ${
                              esHoraSeleccionada
                                ? 'bg-emerald-600 text-white border-emerald-600 shadow-sm'
                                : 'bg-slate-50 dark:bg-gray-800 text-slate-700 dark:text-slate-200 border-slate-200 dark:border-gray-700 hover:border-emerald-500'
                            }`}
                          >
                            {h.label}
                          </button>
                        )
                      })}
                    </div>
                  </div>

                  {/* Tarde */}
                  <div>
                    <span className="text-[10px] font-bold uppercase text-slate-400 tracking-wider block mb-1.5">
                      Tarde
                    </span>
                    <div className="grid grid-cols-4 gap-2">
                      {FRANJAS_HORARIAS.tarde.map((h) => {
                        const esHoraSeleccionada = horaSeleccionada === h.hora
                        return (
                          <button
                            key={h.id}
                            type="button"
                            onClick={() => setHoraSeleccionada(h.hora)}
                            className={`py-2.5 px-3 rounded-xl text-xs font-bold border transition-all cursor-pointer text-center ${
                              esHoraSeleccionada
                                ? 'bg-emerald-600 text-white border-emerald-600 shadow-sm'
                                : 'bg-slate-50 dark:bg-gray-800 text-slate-700 dark:text-slate-200 border-slate-200 dark:border-gray-700 hover:border-emerald-500'
                            }`}
                          >
                            {h.label}
                          </button>
                        )
                      })}
                    </div>
                  </div>
                </div>
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
                      {fechaSeleccionada} —{' '}
                      {
                        [...FRANJAS_HORARIAS.manana, ...FRANJAS_HORARIAS.tarde].find(
                          (h) => h.hora === horaSeleccionada,
                        )?.label
                      }
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
