import React, { useEffect, useMemo, useState } from 'react'
import { useBloqueosStore } from '@/stores/useBloqueosStore'
import type { Bloqueo } from '@/lib/reservaApi'
import {
  Plus,
  Trash2,
  Pencil,
  CalendarDays,
  AlertCircle,
  X,
  Clock3,
  CalendarCheck,
  Ban,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  AlertTriangle,
  ShieldAlert,
  Sparkles,
  Search,
} from 'lucide-react'

const HORARIOS = [
  { hora: '08:00', label: '08:00 AM' },
  { hora: '09:00', label: '09:00 AM' },
  { hora: '10:00', label: '10:00 AM' },
  { hora: '11:00', label: '11:00 AM' },
  { hora: '12:00', label: '12:00 PM' },
  { hora: '13:00', label: '01:00 PM' },
  { hora: '14:00', label: '02:00 PM' },
  { hora: '15:00', label: '03:00 PM' },
  { hora: '16:00', label: '04:00 PM' },
  { hora: '17:00', label: '05:00 PM' },
  { hora: '18:00', label: '06:00 PM' },
  { hora: '19:00', label: '07:00 PM' },
  { hora: '20:00', label: '08:00 PM' },
] as const

const HORA_INICIO_DIA = '08:00'
const HORA_FIN_DIA = '20:00'

function obtenerFechaLocal() {
  const hoy = new Date()
  return [
    hoy.getFullYear(),
    String(hoy.getMonth() + 1).padStart(2, '0'),
    String(hoy.getDate()).padStart(2, '0'),
  ].join('-')
}

function formatearFecha(fecha: string) {
  if (!fecha) return 'Selecciona una fecha'
  const [anio, mes, dia] = fecha.split('-').map(Number)
  return new Date(anio, mes - 1, dia).toLocaleDateString('es-CO', {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  })
}

function formatearHora(hora: string) {
  return HORARIOS.find((h) => h.hora === hora)?.label || hora
}

function SelectorFecha({
  fecha,
  onChange,
}: {
  fecha: string
  onChange: (fecha: string) => void
}) {
  const [abierto, setAbierto] = useState(false)
  const [mesActual, setMesActual] = useState(() => {
    const inicial = fecha ? new Date(`${fecha}T12:00:00`) : new Date()
    return new Date(inicial.getFullYear(), inicial.getMonth(), 1)
  })

  const hoy = obtenerFechaLocal()
  const primerDia = new Date(mesActual.getFullYear(), mesActual.getMonth(), 1).getDay()
  const diasMes = new Date(
    mesActual.getFullYear(),
    mesActual.getMonth() + 1,
    0,
  ).getDate()
  const nombreMes = mesActual.toLocaleDateString('es-CO', {
    month: 'long',
    year: 'numeric',
  })
  const dias = Array.from({ length: primerDia + diasMes }, (_, i) =>
    i < primerDia ? null : i - primerDia + 1,
  )
  const mesActualInicio = `${mesActual.getFullYear()}-${String(mesActual.getMonth() + 1).padStart(2, '0')}-01`
  const puedeRetroceder = mesActualInicio > `${hoy.slice(0, 7)}-01`

  return (
    <div className="relative">
      <label className="mb-2 block text-[11px] font-bold uppercase tracking-[0.12em] text-slate-500 dark:text-slate-400">
        Fecha del bloqueo
      </label>
      <button
        type="button"
        onClick={() => setAbierto((actual) => !actual)}
        className={`group flex w-full items-center gap-3 rounded-2xl border bg-slate-50/80 p-3.5 text-left transition-all dark:bg-slate-800/70 ${
          abierto
            ? 'border-amber-400 ring-4 ring-amber-400/10'
            : 'border-slate-200 hover:border-amber-300 dark:border-slate-700 dark:hover:border-amber-500/60'
        }`}
      >
        <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-amber-400/15 text-amber-600 transition-colors group-hover:bg-amber-400/25 dark:text-amber-400">
          <CalendarDays className="h-5 w-5" />
        </span>
        <span className="min-w-0 flex-1">
          <span className="block text-[10px] font-semibold uppercase tracking-wider text-slate-400">
            Fecha seleccionada
          </span>
          <span className="mt-0.5 block truncate text-sm font-bold capitalize text-slate-800 dark:text-white">
            {fecha ? formatearFecha(fecha) : 'Seleccionar fecha'}
          </span>
        </span>
        <ChevronRight
          className={`h-4 w-4 text-slate-400 transition-transform ${abierto ? 'rotate-90' : ''}`}
        />
      </button>

      {abierto && (
        <div className="absolute left-0 top-full z-[70] mt-2 w-full min-w-[290px] rounded-2xl border border-slate-200 bg-white p-4 shadow-2xl shadow-slate-900/10 dark:border-slate-700 dark:bg-slate-900">
          <div className="mb-4 flex items-center justify-between">
            <button
              type="button"
              onClick={() =>
                setMesActual(
                  new Date(mesActual.getFullYear(), mesActual.getMonth() - 1, 1),
                )
              }
              disabled={!puedeRetroceder}
              className="rounded-xl p-2 text-slate-500 transition hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-25 dark:hover:bg-slate-800"
              aria-label="Mes anterior"
            >
              <ChevronLeft className="h-4 w-4" />
            </button>
            <h3 className="text-sm font-extrabold capitalize text-slate-800 dark:text-white">
              {nombreMes}
            </h3>
            <button
              type="button"
              onClick={() =>
                setMesActual(
                  new Date(mesActual.getFullYear(), mesActual.getMonth() + 1, 1),
                )
              }
              className="rounded-xl p-2 text-slate-500 transition hover:bg-slate-100 dark:hover:bg-slate-800"
              aria-label="Mes siguiente"
            >
              <ChevronRight className="h-4 w-4" />
            </button>
          </div>

          <div className="mb-1 grid grid-cols-7">
            {['DO', 'LU', 'MA', 'MI', 'JU', 'VI', 'SA'].map((dia) => (
              <span
                key={dia}
                className="py-2 text-center text-[10px] font-extrabold text-slate-400"
              >
                {dia}
              </span>
            ))}
          </div>
          <div className="grid grid-cols-7 gap-1">
            {dias.map((dia, index) => {
              if (dia === null) return <span key={`vacio-${index}`} />
              const fechaDia = `${mesActual.getFullYear()}-${String(mesActual.getMonth() + 1).padStart(2, '0')}-${String(dia).padStart(2, '0')}`
              const pasado = fechaDia < hoy
              const seleccionado = fecha === fechaDia
              const esHoy = fechaDia === hoy
              return (
                <button
                  key={fechaDia}
                  type="button"
                  disabled={pasado}
                  onClick={() => {
                    onChange(fechaDia)
                    setAbierto(false)
                  }}
                  className={`aspect-square rounded-xl text-xs font-bold transition-all disabled:cursor-not-allowed disabled:opacity-20 ${
                    seleccionado
                      ? 'bg-amber-400 text-slate-950 shadow-lg shadow-amber-400/25'
                      : esHoy
                        ? 'border border-amber-400 text-amber-600 dark:text-amber-400'
                        : 'text-slate-600 hover:bg-amber-50 hover:text-amber-700 dark:text-slate-300 dark:hover:bg-amber-400/10'
                  }`}
                >
                  {dia}
                </button>
              )
            })}
          </div>
          <div className="mt-3 flex items-center justify-between border-t border-slate-100 pt-3 dark:border-slate-800">
            <button
              type="button"
              onClick={() => {
                onChange('')
                setAbierto(false)
              }}
              className="text-xs font-semibold text-slate-400 transition hover:text-red-500"
            >
              Limpiar fecha
            </button>
            <button
              type="button"
              onClick={() => {
                const ahora = new Date()
                setMesActual(new Date(ahora.getFullYear(), ahora.getMonth(), 1))
                onChange(hoy)
                setAbierto(false)
              }}
              className="rounded-lg px-3 py-1.5 text-xs font-bold text-amber-700 transition hover:bg-amber-50 dark:text-amber-400 dark:hover:bg-amber-400/10"
            >
              Ir a hoy
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

function SelectorHorarios({
  titulo,
  horaSeleccionada,
  onSeleccionar,
  excluirDesde,
  excluirHasta,
}: {
  titulo: string
  horaSeleccionada: string
  onSeleccionar: (hora: string) => void
  excluirDesde?: string
  excluirHasta?: string
}) {
  return (
    <section>
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <h3 className="text-xs font-extrabold uppercase tracking-[0.08em] text-slate-700 dark:text-slate-200">
          {titulo}
        </h3>

        <span
          className={`rounded-lg px-2.5 py-1 text-[10px] font-extrabold ${
            horaSeleccionada
              ? 'bg-amber-400/15 text-amber-700 dark:text-amber-400'
              : 'bg-slate-100 text-slate-400 dark:bg-slate-800'
          }`}
        >
          {horaSeleccionada ? formatearHora(horaSeleccionada) : 'Sin seleccionar'}
        </span>
      </div>

      <div className="grid grid-cols-3 gap-2 sm:grid-cols-4">
        {HORARIOS.map((h) => {
          const activo = horaSeleccionada === h.hora

          // Solo se aplican restricciones si existe una hora contraria.
          // La hora activa nunca se deshabilita porque debe poder deseleccionarse.
          const invalido =
            !activo &&
            ((Boolean(excluirDesde) && h.hora <= excluirDesde!) ||
              (Boolean(excluirHasta) && h.hora >= excluirHasta!))

          return (
            <button
              key={h.hora}
              type="button"
              disabled={invalido}
              onClick={() => onSeleccionar(activo ? '' : h.hora)}
              aria-pressed={activo}
              title={
                activo
                  ? 'Pulsa para deseleccionar este horario'
                  : invalido
                    ? 'Horario no disponible para este rango'
                    : 'Seleccionar horario'
              }
              className={`flex min-h-[44px] items-center justify-center gap-1.5 rounded-xl border px-2 py-2 text-[11px] font-extrabold transition-all duration-200 focus:outline-none focus:ring-4 focus:ring-amber-400/20 disabled:cursor-not-allowed disabled:opacity-25 ${
                activo
                  ? 'scale-[1.02] border-amber-400 bg-amber-400 text-slate-950 shadow-md shadow-amber-400/25 ring-2 ring-amber-400/20'
                  : 'border-slate-200 bg-white text-slate-600 hover:-translate-y-0.5 hover:border-amber-400 hover:bg-amber-50 hover:text-amber-800 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300 dark:hover:border-amber-500 dark:hover:bg-amber-400/10 dark:hover:text-amber-300'
              }`}
            >
              {activo && <CheckCircle2 className="h-3.5 w-3.5 shrink-0" />}
              {h.label}
            </button>
          )
        })}
      </div>

      <p className="mt-2 text-[10px] text-slate-400 dark:text-slate-500">
        Pulsa nuevamente la hora seleccionada para desmarcarla.
      </p>
    </section>
  )
}

export function BloqueosManager() {
  const {
    bloqueos,
    isLoading,
    error,
    fetchBloqueos,
    crearBloqueo,
    actualizarBloqueo,
    eliminarBloqueo,
  } = useBloqueosStore()

  const [modalAbierto, setModalAbierto] = useState(false)
  const [bloqueoEditando, setBloqueoEditando] = useState<string | null>(null)
  const [fecha, setFecha] = useState('')
  const [horaInicio, setHoraInicio] = useState('')
  const [horaFin, setHoraFin] = useState('')
  const [motivo, setMotivo] = useState('')
  const [diaCompleto, setDiaCompleto] = useState(false)
  const [errorLocal, setErrorLocal] = useState<string | null>(null)
  const [guardado, setGuardado] = useState(false)
  const [bloqueoAEliminar, setBloqueoAEliminar] = useState<string | null>(null)
  const [eliminando, setEliminando] = useState(false)
  const [errorEliminar, setErrorEliminar] = useState<string | null>(null)
  const [busqueda, setBusqueda] = useState('')

  useEffect(() => {
    fetchBloqueos().catch(() => undefined)
  }, [fetchBloqueos])

  const limpiarFormulario = () => {
    setFecha('')
    setHoraInicio('')
    setHoraFin('')
    setMotivo('')
    setDiaCompleto(false)
    setErrorLocal(null)
    setGuardado(false)
    setBloqueoEditando(null)
  }

  const abrirModal = () => {
    limpiarFormulario()
    setModalAbierto(true)
  }

  const abrirEdicion = (bloqueo: Bloqueo) => {
    setFecha(bloqueo.fecha)
    setHoraInicio(bloqueo.horaInicio)
    setHoraFin(bloqueo.horaFin)
    setMotivo(bloqueo.motivo)
    setDiaCompleto(
      bloqueo.horaInicio === HORA_INICIO_DIA && bloqueo.horaFin === HORA_FIN_DIA,
    )
    setErrorLocal(null)
    setGuardado(false)
    setBloqueoEditando(bloqueo.id)
    setModalAbierto(true)
  }

  const cerrarModal = () => {
    if (isLoading) return
    setModalAbierto(false)
    limpiarFormulario()
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setErrorLocal(null)

    if (!fecha || !motivo.trim()) {
      setErrorLocal('Completa la fecha y el motivo del bloqueo.')
      return
    }
    if (!diaCompleto && (!horaInicio || !horaFin)) {
      setErrorLocal('Selecciona las horas de inicio y finalización.')
      return
    }
    if (fecha < obtenerFechaLocal()) {
      setErrorLocal('No puedes bloquear fechas en el pasado.')
      return
    }

    const inicio = diaCompleto ? HORA_INICIO_DIA : horaInicio
    const fin = diaCompleto ? HORA_FIN_DIA : horaFin
    if (inicio >= fin) {
      setErrorLocal('La hora de finalización debe ser posterior a la de inicio.')
      return
    }

    try {
      const datosBloqueo = {
        barberoId: 1,
        fecha,
        horaInicio: inicio,
        horaFin: fin,
        motivo: motivo.trim(),
      }
      if (bloqueoEditando) {
        await actualizarBloqueo(bloqueoEditando, datosBloqueo)
      } else {
        await crearBloqueo(datosBloqueo)
      }
      setGuardado(true)
      window.setTimeout(() => {
        setModalAbierto(false)
        limpiarFormulario()
      }, 750)
    } catch (err) {
      setErrorLocal(
        err instanceof Error ? err.message : 'No fue posible guardar el bloqueo.',
      )
    }
  }

  const confirmarEliminar = async () => {
    if (bloqueoAEliminar === null) return
    try {
      setEliminando(true)
      setErrorEliminar(null)
      await eliminarBloqueo(bloqueoAEliminar)
      setBloqueoAEliminar(null)
    } catch {
      setErrorEliminar('No se pudo eliminar el bloqueo. Inténtalo de nuevo.')
    } finally {
      setEliminando(false)
    }
  }

  const bloqueoSeleccionado = useMemo(
    () => bloqueos.find((b) => b.id === bloqueoAEliminar),
    [bloqueos, bloqueoAEliminar],
  )

  const bloqueosFiltrados = useMemo(() => {
    const termino = busqueda.trim().toLocaleLowerCase('es')
    return [...bloqueos]
      .filter(
        (b) =>
          !termino ||
          b.motivo.toLocaleLowerCase('es').includes(termino) ||
          formatearFecha(b.fecha).toLocaleLowerCase('es').includes(termino),
      )
      .sort((a, b) =>
        `${a.fecha}-${a.horaInicio}`.localeCompare(`${b.fecha}-${b.horaInicio}`),
      )
  }, [bloqueos, busqueda])

  const hoy = obtenerFechaLocal()
  const bloqueosProximos = bloqueos.filter((b) => b.fecha >= hoy).length

  return (
    <main className="mx-auto w-full max-w-6xl space-y-6 pb-8">
      {/* Encabezado */}
      <header className="relative isolate overflow-hidden rounded-[28px] bg-slate-950 px-6 py-7 text-white shadow-xl shadow-slate-950/10 sm:px-8 sm:py-8">
        <div className="absolute -right-12 -top-24 -z-10 h-64 w-64 rounded-full bg-amber-400/20 blur-3xl" />
        <div className="absolute -bottom-24 right-1/3 -z-10 h-48 w-48 rounded-full bg-orange-500/10 blur-3xl" />
        <div className="flex flex-col gap-5 sm:flex-row sm:items-center sm:justify-between">
          <div className="max-w-xl">
            <div className="mb-3 inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/10 px-3 py-1.5 text-[10px] font-bold uppercase tracking-[0.16em] text-amber-300">
              <Sparkles className="h-3.5 w-3.5" />
              Administración de agenda
            </div>
            <h1 className="text-2xl font-black tracking-tight sm:text-3xl">
              Gestión de bloqueos
            </h1>
            <p className="mt-2 max-w-lg text-sm leading-relaxed text-slate-300">
              Organiza los horarios no disponibles y mantén tu agenda bajo control.
            </p>
          </div>
          <button
            type="button"
            onClick={abrirModal}
            className="inline-flex shrink-0 items-center justify-center gap-2 rounded-2xl bg-amber-400 px-5 py-3.5 text-xs font-black text-slate-950 shadow-lg shadow-amber-400/20 transition hover:-translate-y-0.5 hover:bg-amber-300 hover:shadow-amber-400/30 focus:outline-none focus:ring-4 focus:ring-amber-300/30"
          >
            <Plus className="h-4 w-4" />
            Crear bloqueo
          </button>
        </div>
      </header>

      {/* Indicadores */}
      <section className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <div className="group rounded-2xl border border-slate-200/80 bg-white p-5 shadow-sm transition hover:-translate-y-0.5 hover:shadow-md dark:border-slate-800 dark:bg-slate-900">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500 dark:text-slate-400">
              Bloqueos registrados
            </span>
            <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300">
              <Ban className="h-5 w-5" />
            </span>
          </div>
          <p className="mt-3 text-3xl font-black tracking-tight text-slate-900 dark:text-white">
            {bloqueos.length}
          </p>
          <p className="mt-1 text-[11px] text-slate-400">Registros en la agenda</p>
        </div>
        <div className="group rounded-2xl border border-slate-200/80 bg-white p-5 shadow-sm transition hover:-translate-y-0.5 hover:shadow-md dark:border-slate-800 dark:bg-slate-900">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500 dark:text-slate-400">
              Próximos bloqueos
            </span>
            <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-amber-400/15 text-amber-600 dark:text-amber-400">
              <CalendarDays className="h-5 w-5" />
            </span>
          </div>
          <p className="mt-3 text-3xl font-black tracking-tight text-slate-900 dark:text-white">
            {bloqueosProximos}
          </p>
          <p className="mt-1 text-[11px] text-slate-400">Hoy y fechas futuras</p>
        </div>
        <div className="group rounded-2xl border border-slate-200/80 bg-white p-5 shadow-sm transition hover:-translate-y-0.5 hover:shadow-md dark:border-slate-800 dark:bg-slate-900">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500 dark:text-slate-400">
              Estado de la agenda
            </span>
            <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">
              <CalendarCheck className="h-5 w-5" />
            </span>
          </div>
          <p className="mt-3 text-lg font-black text-emerald-600 dark:text-emerald-400">
            Gestión activa
          </p>
          <p className="mt-1 text-[11px] text-slate-400">Control de disponibilidad</p>
        </div>
      </section>

      {/* Lista */}
      <section className="overflow-hidden rounded-[26px] border border-slate-200/80 bg-white shadow-sm dark:border-slate-800 dark:bg-slate-900">
        <div className="flex flex-col gap-4 border-b border-slate-100 px-5 py-5 dark:border-slate-800 sm:flex-row sm:items-center sm:justify-between sm:px-7">
          <div>
            <div className="flex items-center gap-2">
              <span className="h-2 w-2 rounded-full bg-emerald-500 ring-4 ring-emerald-500/10" />
              <h2 className="text-base font-black text-slate-900 dark:text-white">
                Bloqueos de agenda
              </h2>
            </div>
            <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
              Consulta, modifica o elimina periodos no disponibles.
            </p>
          </div>
          <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
            <label className="relative block">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
              <input
                type="search"
                value={busqueda}
                onChange={(e) => setBusqueda(e.target.value)}
                placeholder="Buscar por motivo o fecha"
                className="w-full rounded-xl border border-slate-200 bg-slate-50 py-2.5 pl-9 pr-3 text-xs text-slate-700 outline-none transition placeholder:text-slate-400 focus:border-amber-400 focus:ring-4 focus:ring-amber-400/10 dark:border-slate-700 dark:bg-slate-800 dark:text-white sm:w-56"
              />
            </label>
            <span className="inline-flex items-center justify-center rounded-xl bg-slate-100 px-3 py-2.5 text-[10px] font-extrabold uppercase tracking-wider text-slate-500 dark:bg-slate-800 dark:text-slate-300">
              {bloqueos.length} {bloqueos.length === 1 ? 'registro' : 'registros'}
            </span>
          </div>
        </div>

        <div className="p-5 sm:p-7">
          {isLoading && bloqueos.length === 0 ? (
            <div className="flex flex-col items-center py-14 text-center">
              <span className="mb-3 h-8 w-8 animate-spin rounded-full border-[3px] border-slate-200 border-t-amber-400 dark:border-slate-700 dark:border-t-amber-400" />
              <p className="text-sm font-semibold text-slate-600 dark:text-slate-300">
                Cargando bloqueos...
              </p>
              <p className="mt-1 text-xs text-slate-400">
                Estamos actualizando la agenda.
              </p>
            </div>
          ) : error && bloqueos.length === 0 ? (
            <div className="rounded-2xl border border-red-200 bg-red-50 p-5 text-center dark:border-red-900/50 dark:bg-red-950/20">
              <AlertCircle className="mx-auto mb-2 h-6 w-6 text-red-500" />
              <p className="text-sm font-bold text-red-700 dark:text-red-400">
                No se pudieron cargar los bloqueos
              </p>
              <p className="mt-1 text-xs text-red-600/80 dark:text-red-400/80">
                {error}
              </p>
              <button
                type="button"
                onClick={() => fetchBloqueos()}
                className="mt-3 rounded-lg bg-red-600 px-4 py-2 text-xs font-bold text-white transition hover:bg-red-700"
              >
                Reintentar
              </button>
            </div>
          ) : bloqueosFiltrados.length === 0 ? (
            <div className="rounded-2xl border border-dashed border-slate-200 bg-slate-50/70 px-5 py-14 text-center dark:border-slate-700 dark:bg-slate-800/30">
              <span className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-amber-400/15 text-amber-600 dark:text-amber-400">
                <CalendarDays className="h-7 w-7" />
              </span>
              <h3 className="text-sm font-extrabold text-slate-800 dark:text-white">
                {busqueda ? 'No encontramos resultados' : 'Tu agenda está despejada'}
              </h3>
              <p className="mx-auto mt-1 max-w-sm text-xs leading-relaxed text-slate-500 dark:text-slate-400">
                {busqueda
                  ? 'Prueba con otro motivo o una fecha diferente.'
                  : 'Cuando registres un bloqueo, aparecerá aquí para que puedas administrarlo.'}
              </p>
              {!busqueda && (
                <button
                  type="button"
                  onClick={abrirModal}
                  className="mt-5 inline-flex items-center gap-2 rounded-xl bg-slate-900 px-4 py-2.5 text-xs font-bold text-white transition hover:bg-slate-800 dark:bg-amber-400 dark:text-slate-950 dark:hover:bg-amber-300"
                >
                  <Plus className="h-4 w-4" /> Crear primer bloqueo
                </button>
              )}
            </div>
          ) : (
            <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
              {bloqueosFiltrados.map((b) => (
                <article
                  key={b.id}
                  data-testid={`bloqueo-item-${b.id}`}
                  className="group relative isolate overflow-hidden rounded-2xl border border-slate-200 bg-white p-5 transition-all duration-300 hover:-translate-y-1 hover:border-amber-300 hover:shadow-xl hover:shadow-slate-900/[0.06] dark:border-slate-700 dark:bg-slate-900 dark:hover:border-amber-500/50 dark:hover:shadow-black/20"
                >
                  <span className="absolute inset-y-0 left-0 w-1 bg-slate-200 transition-colors duration-300 group-hover:bg-amber-400 dark:bg-slate-700" />
                  <span className="pointer-events-none absolute -left-1/2 top-0 h-full w-1/2 -skew-x-12 bg-gradient-to-r from-transparent via-amber-300/20 to-transparent opacity-0 transition-all duration-700 ease-out group-hover:left-[130%] group-hover:opacity-100" />
                  <div className="relative flex gap-4 pl-2">
                    <div className="hidden h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-amber-400/15 text-amber-600 sm:flex dark:text-amber-400">
                      <ShieldAlert className="h-6 w-6" />
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="flex items-start justify-between gap-3">
                        <div className="min-w-0">
                          <span className="mb-1 inline-flex rounded-md bg-amber-400/15 px-2 py-1 text-[9px] font-black uppercase tracking-[0.12em] text-amber-700 dark:text-amber-400">
                            No disponible
                          </span>
                          <h3 className="break-words text-sm font-extrabold text-slate-900 dark:text-white">
                            {b.motivo}
                          </h3>
                        </div>
                        <div className="flex shrink-0 items-center gap-1">
                          <button
                            type="button"
                            onClick={() => abrirEdicion(b)}
                            title="Editar bloqueo"
                            aria-label="Editar bloqueo"
                            className="rounded-xl border border-transparent p-2 text-slate-400 transition hover:border-blue-100 hover:bg-blue-50 hover:text-blue-600 dark:hover:border-blue-900/50 dark:hover:bg-blue-950/30 dark:hover:text-blue-400"
                          >
                            <Pencil className="h-4 w-4" />
                          </button>
                          <button
                            type="button"
                            onClick={() => {
                              setErrorEliminar(null)
                              setBloqueoAEliminar(b.id)
                            }}
                            title="Eliminar bloqueo"
                            aria-label="Eliminar bloqueo"
                            className="rounded-xl border border-transparent p-2 text-slate-400 transition hover:border-red-100 hover:bg-red-50 hover:text-red-600 dark:hover:border-red-900/50 dark:hover:bg-red-950/30 dark:hover:text-red-400"
                          >
                            <Trash2 className="h-4 w-4" />
                          </button>
                        </div>
                      </div>
                      <div className="mt-4 grid grid-cols-1 gap-2 sm:grid-cols-2">
                        <div className="flex min-w-0 items-center gap-2 rounded-xl bg-slate-50 px-3 py-2.5 dark:bg-slate-800/70">
                          <CalendarDays className="h-4 w-4 shrink-0 text-amber-500" />
                          <span className="truncate text-[11px] font-semibold capitalize text-slate-600 dark:text-slate-300">
                            {formatearFecha(b.fecha)}
                          </span>
                        </div>
                        <div className="flex items-center gap-2 rounded-xl bg-slate-50 px-3 py-2.5 dark:bg-slate-800/70">
                          <Clock3 className="h-4 w-4 shrink-0 text-amber-500" />
                          <span className="text-[11px] font-semibold text-slate-600 dark:text-slate-300">
                            {formatearHora(b.horaInicio)} – {formatearHora(b.horaFin)}
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>
                </article>
              ))}
            </div>
          )}
        </div>
      </section>

      {/* Modal crear / editar */}
      {modalAbierto && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center overflow-y-auto bg-slate-950/65 p-3 backdrop-blur-sm sm:p-5"
          onMouseDown={(e) => {
            if (e.target === e.currentTarget) cerrarModal()
          }}
        >
          <div
            role="dialog"
            aria-modal="true"
            aria-labelledby="titulo-modal-bloqueo"
            className="my-auto max-h-[94vh] w-full max-w-[620px] overflow-y-auto rounded-[26px] border border-white/10 bg-white shadow-2xl shadow-black/30 dark:bg-slate-900"
          >
            <div className="sticky top-0 z-20 flex items-start justify-between border-b border-slate-100 bg-white/95 px-5 py-5 backdrop-blur sm:px-7 dark:border-slate-800 dark:bg-slate-900/95">
              <div className="flex items-start gap-3">
                <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-amber-400/15 text-amber-600 dark:text-amber-400">
                  {bloqueoEditando ? (
                    <Pencil className="h-5 w-5" />
                  ) : (
                    <CalendarCheck className="h-5 w-5" />
                  )}
                </span>
                <div>
                  <h2
                    id="titulo-modal-bloqueo"
                    className="text-lg font-black text-slate-900 dark:text-white sm:text-xl"
                  >
                    {bloqueoEditando ? 'Editar bloqueo' : 'Nuevo bloqueo'}
                  </h2>
                  <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                    Define cuándo y por qué no estará disponible la agenda.
                  </p>
                </div>
              </div>
              <button
                type="button"
                onClick={cerrarModal}
                disabled={isLoading}
                aria-label="Cerrar modal"
                className="rounded-xl bg-slate-100 p-2.5 text-slate-500 transition hover:bg-slate-200 hover:text-slate-900 disabled:opacity-40 dark:bg-slate-800 dark:text-slate-400 dark:hover:bg-slate-700 dark:hover:text-white"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <form
              onSubmit={handleSubmit}
              className="space-y-5 px-5 py-5 sm:px-7 sm:py-6"
            >
              <SelectorFecha fecha={fecha} onChange={setFecha} />

              <div>
                <label
                  htmlFor="motivo-bloqueo"
                  className="mb-2 block text-[11px] font-bold uppercase tracking-[0.12em] text-slate-500 dark:text-slate-400"
                >
                  Motivo del bloqueo
                </label>
                <input
                  id="motivo-bloqueo"
                  type="text"
                  data-testid="input-motivo"
                  value={motivo}
                  onChange={(e) => setMotivo(e.target.value)}
                  placeholder="Ej. Cita médica, mantenimiento, asunto personal..."
                  maxLength={100}
                  className="w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3.5 text-sm font-medium text-slate-800 outline-none transition placeholder:font-normal placeholder:text-slate-400 focus:border-amber-400 focus:bg-white focus:ring-4 focus:ring-amber-400/10 dark:border-slate-700 dark:bg-slate-800 dark:text-white dark:focus:bg-slate-800"
                />
                <p className="mt-1.5 text-right text-[10px] text-slate-400">
                  {motivo.length}/100
                </p>
              </div>

              <div className="rounded-2xl border border-slate-200 bg-slate-50/70 p-4 dark:border-slate-700 dark:bg-slate-800/40">
                <div className="mb-3 flex items-center justify-between gap-3">
                  <div>
                    <h3 className="text-xs font-extrabold text-slate-800 dark:text-white">
                      Duración del bloqueo
                    </h3>
                    <p className="mt-1 text-[10px] text-slate-500 dark:text-slate-400">
                      Elige un rango horario o bloquea toda la jornada.
                    </p>
                  </div>
                  <Clock3 className="h-5 w-5 text-amber-500" />
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <button
                    type="button"
                    onClick={() => setDiaCompleto(false)}
                    className={`rounded-xl border px-3 py-3 text-left transition ${
                      !diaCompleto
                        ? 'border-amber-400 bg-amber-400/10 ring-2 ring-amber-400/10'
                        : 'border-slate-200 bg-white hover:border-slate-300 dark:border-slate-700 dark:bg-slate-900 dark:hover:border-slate-600'
                    }`}
                  >
                    <Clock3
                      className={`mb-2 h-4 w-4 ${!diaCompleto ? 'text-amber-600 dark:text-amber-400' : 'text-slate-400'}`}
                    />
                    <span className="block text-xs font-extrabold text-slate-800 dark:text-white">
                      Por horas
                    </span>
                    <span className="mt-0.5 block text-[10px] text-slate-500">
                      Rango personalizado
                    </span>
                  </button>
                  <button
                    type="button"
                    onClick={() => setDiaCompleto(true)}
                    className={`rounded-xl border px-3 py-3 text-left transition ${
                      diaCompleto
                        ? 'border-amber-400 bg-amber-400/10 ring-2 ring-amber-400/10'
                        : 'border-slate-200 bg-white hover:border-slate-300 dark:border-slate-700 dark:bg-slate-900 dark:hover:border-slate-600'
                    }`}
                  >
                    <CalendarCheck
                      className={`mb-2 h-4 w-4 ${diaCompleto ? 'text-amber-600 dark:text-amber-400' : 'text-slate-400'}`}
                    />
                    <span className="block text-xs font-extrabold text-slate-800 dark:text-white">
                      Día completo
                    </span>
                    <span className="mt-0.5 block text-[10px] text-slate-500">
                      08:00 AM – 08:00 PM
                    </span>
                  </button>
                </div>
              </div>

              {!diaCompleto ? (
                <div className="space-y-5">
                  <SelectorHorarios
                    titulo="Hora de inicio"
                    horaSeleccionada={horaInicio}
                    onSeleccionar={(hora) => {
                      setHoraInicio(hora)
                      setErrorLocal(null)
                      if (horaFin && hora >= horaFin) setHoraFin('')
                    }}
                    excluirHasta={horaFin}
                  />
                  <div className="border-t border-dashed border-slate-200 dark:border-slate-700" />
                  <SelectorHorarios
                    titulo="Hora de finalización"
                    horaSeleccionada={horaFin}
                    onSeleccionar={(hora) => {
                      setHoraFin(hora)
                      setErrorLocal(null)
                    }}
                    excluirDesde={horaInicio}
                  />
                </div>
              ) : (
                <div className="flex items-center gap-3 rounded-2xl border border-amber-200 bg-amber-50 p-4 dark:border-amber-900/50 dark:bg-amber-950/20">
                  <CalendarCheck className="h-5 w-5 shrink-0 text-amber-600 dark:text-amber-400" />
                  <div>
                    <p className="text-xs font-extrabold text-slate-800 dark:text-white">
                      Jornada completa seleccionada
                    </p>
                    <p className="mt-1 text-[11px] text-slate-600 dark:text-slate-400">
                      El bloqueo cubrirá de 08:00 AM a 08:00 PM.
                    </p>
                  </div>
                </div>
              )}

              {errorLocal && (
                <div
                  data-testid="error-bloqueo"
                  role="alert"
                  className="flex items-start gap-2 rounded-xl border border-red-200 bg-red-50 p-3 text-red-700 dark:border-red-900/50 dark:bg-red-950/30 dark:text-red-400"
                >
                  <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
                  <p className="text-xs font-semibold">{errorLocal}</p>
                </div>
              )}
              {guardado && (
                <div className="flex items-center gap-2 rounded-xl border border-emerald-200 bg-emerald-50 p-3 text-emerald-700 dark:border-emerald-900/50 dark:bg-emerald-950/20 dark:text-emerald-400">
                  <CheckCircle2 className="h-4 w-4" />
                  <p className="text-xs font-bold">
                    {bloqueoEditando
                      ? 'Cambios guardados correctamente.'
                      : 'Bloqueo registrado correctamente.'}
                  </p>
                </div>
              )}

              <div className="rounded-2xl bg-slate-950 p-4 text-white">
                <div className="mb-2 flex items-center gap-2 text-[10px] font-black uppercase tracking-[0.14em] text-amber-300">
                  <Sparkles className="h-3.5 w-3.5" /> Resumen
                </div>
                <p className="text-xs font-bold capitalize">
                  {fecha ? formatearFecha(fecha) : 'Selecciona una fecha'}
                </p>
                <p className="mt-1 text-[11px] text-slate-300">
                  {diaCompleto
                    ? 'Jornada completa · 08:00 AM – 08:00 PM'
                    : horaInicio && horaFin
                      ? `${formatearHora(horaInicio)} – ${formatearHora(horaFin)}`
                      : 'Selecciona la hora de inicio y finalización'}
                </p>
                {motivo.trim() && (
                  <p className="mt-1 truncate text-[11px] text-slate-400">
                    Motivo: {motivo.trim()}
                  </p>
                )}
              </div>

              <div className="flex flex-col-reverse gap-2 border-t border-slate-100 pt-4 sm:flex-row sm:justify-end dark:border-slate-800">
                <button
                  type="button"
                  onClick={cerrarModal}
                  disabled={isLoading}
                  className="rounded-xl border border-slate-200 px-5 py-3 text-xs font-bold text-slate-600 transition hover:bg-slate-50 disabled:opacity-40 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  data-testid="btn-registrar-bloqueo"
                  disabled={
                    isLoading ||
                    guardado ||
                    !fecha ||
                    !motivo.trim() ||
                    (!diaCompleto && (!horaInicio || !horaFin))
                  }
                  className="inline-flex items-center justify-center gap-2 rounded-xl bg-amber-400 px-5 py-3 text-xs font-black text-slate-950 shadow-lg shadow-amber-400/15 transition hover:-translate-y-0.5 hover:bg-amber-300 disabled:cursor-not-allowed disabled:opacity-40"
                >
                  {isLoading ? (
                    <>
                      <span className="h-4 w-4 animate-spin rounded-full border-2 border-slate-900/30 border-t-slate-900" />
                      Guardando...
                    </>
                  ) : (
                    <>
                      {bloqueoEditando ? (
                        <CheckCircle2 className="h-4 w-4" />
                      ) : (
                        <Plus className="h-4 w-4" />
                      )}
                      {bloqueoEditando ? 'Guardar cambios' : 'Confirmar bloqueo'}
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Confirmación de eliminación */}
      {bloqueoAEliminar !== null && (
        <div
          className="fixed inset-0 z-[60] flex items-center justify-center bg-slate-950/65 p-4 backdrop-blur-sm"
          onMouseDown={(e) => {
            if (e.target === e.currentTarget && !eliminando) {
              setBloqueoAEliminar(null)
              setErrorEliminar(null)
            }
          }}
        >
          <div
            role="alertdialog"
            aria-modal="true"
            aria-labelledby="titulo-eliminar-bloqueo"
            className="w-full max-w-[420px] rounded-[26px] border border-white/10 bg-white p-6 shadow-2xl shadow-black/30 dark:bg-slate-900"
          >
            <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-2xl bg-red-50 text-red-600 dark:bg-red-950/40 dark:text-red-400">
              <AlertTriangle className="h-6 w-6" />
            </div>
            <h2
              id="titulo-eliminar-bloqueo"
              className="text-lg font-black text-slate-900 dark:text-white"
            >
              ¿Eliminar este bloqueo?
            </h2>
            <p className="mt-2 text-xs leading-relaxed text-slate-500 dark:text-slate-400">
              Esta acción quitará el bloqueo de la agenda y volverá a habilitar ese
              horario para reservas.
            </p>

            {bloqueoSeleccionado && (
              <div className="mt-4 rounded-2xl border border-slate-200 bg-slate-50 p-4 dark:border-slate-700 dark:bg-slate-800/70">
                <p className="text-sm font-extrabold text-slate-800 dark:text-white">
                  {bloqueoSeleccionado.motivo}
                </p>
                <p className="mt-2 flex items-center gap-2 text-[11px] capitalize text-slate-500 dark:text-slate-400">
                  <CalendarDays className="h-3.5 w-3.5 text-amber-500" />
                  {formatearFecha(bloqueoSeleccionado.fecha)}
                </p>
                <p className="mt-1 flex items-center gap-2 text-[11px] text-slate-500 dark:text-slate-400">
                  <Clock3 className="h-3.5 w-3.5 text-amber-500" />
                  {formatearHora(bloqueoSeleccionado.horaInicio)} –{' '}
                  {formatearHora(bloqueoSeleccionado.horaFin)}
                </p>
              </div>
            )}

            {errorEliminar && (
              <p
                role="alert"
                className="mt-3 text-xs font-semibold text-red-600 dark:text-red-400"
              >
                {errorEliminar}
              </p>
            )}

            <div className="mt-6 flex flex-col-reverse gap-2 sm:flex-row">
              <button
                type="button"
                onClick={() => {
                  if (!eliminando) {
                    setBloqueoAEliminar(null)
                    setErrorEliminar(null)
                  }
                }}
                disabled={eliminando}
                className="flex-1 rounded-xl border border-slate-200 px-4 py-3 text-xs font-bold text-slate-600 transition hover:bg-slate-50 disabled:opacity-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
              >
                Cancelar
              </button>
              <button
                type="button"
                onClick={confirmarEliminar}
                disabled={eliminando}
                className="flex-1 inline-flex items-center justify-center gap-2 rounded-xl bg-red-600 px-4 py-3 text-xs font-black text-white transition hover:bg-red-700 disabled:opacity-50"
              >
                {eliminando ? (
                  <>
                    <span className="h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white" />
                    Eliminando...
                  </>
                ) : (
                  <>
                    <Trash2 className="h-4 w-4" />
                    Sí, eliminar
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </main>
  )
}
