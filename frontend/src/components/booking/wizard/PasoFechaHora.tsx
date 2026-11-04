import { ChevronLeft, ChevronRight } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { listarFranjas, type FranjaHoraria } from '@/lib/reservaApi'
import { useReservaWizardStore } from '@/stores/useReservaWizardStore'
import { cn } from '@/lib/utils'
import { aIso, diaMes, fechaLocal } from './formato'

const DIAS = ['L', 'M', 'M', 'J', 'V', 'S', 'D']

/** Celdas del mes con semanas completas (lunes a domingo). */
function celdasDelMes(anio: number, mes: number): Date[] {
  const primero = new Date(anio, mes, 1)
  const offset = (primero.getDay() + 6) % 7
  const total = Math.ceil((offset + new Date(anio, mes + 1, 0).getDate()) / 7) * 7
  return Array.from({ length: total }, (_, i) => new Date(anio, mes, 1 - offset + i))
}

export function PasoFechaHora() {
  const barbero = useReservaWizardStore((s) => s.barbero)
  const fecha = useReservaWizardStore((s) => s.fecha)
  const hora = useReservaWizardStore((s) => s.hora)
  const seleccionarFecha = useReservaWizardStore((s) => s.seleccionarFecha)
  const seleccionarHora = useReservaWizardStore((s) => s.seleccionarHora)
  const [cargado, setCargado] = useState<{
    clave: string
    franjas: FranjaHoraria[]
  } | null>(null)

  const hoy = useMemo(() => aIso(new Date()), [])
  const [mesVisto, setMesVisto] = useState(() => {
    const base = fechaLocal(fecha ?? hoy)
    return new Date(base.getFullYear(), base.getMonth(), 1)
  })

  useEffect(() => {
    if (!fecha) seleccionarFecha(hoy)
  }, [fecha, hoy, seleccionarFecha])

  useEffect(() => {
    if (!barbero || !fecha) return
    let activo = true
    const clave = `${barbero.id}|${fecha}`
    void listarFranjas(barbero.id, fecha).then((franjas) => {
      if (activo) setCargado({ clave, franjas })
    })
    return () => {
      activo = false
    }
  }, [barbero, fecha])

  const franjas =
    cargado && cargado.clave === `${barbero?.id}|${fecha}` ? cargado.franjas : null
  const celdas = celdasDelMes(mesVisto.getFullYear(), mesVisto.getMonth())
  const mesActual = hoy.slice(0, 7) === aIso(mesVisto).slice(0, 7)
  const mesTexto = mesVisto.toLocaleDateString('es-CO', {
    month: 'long',
    year: 'numeric',
  })
  const tituloMes =
    mesTexto.charAt(0).toUpperCase() + mesTexto.slice(1).replace(' De ', ' de ')

  const mover = (delta: number) =>
    setMesVisto(new Date(mesVisto.getFullYear(), mesVisto.getMonth() + delta, 1))

  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,320px)_1fr]">
      <div className="rounded-2xl border border-slate-200 dark:border-white/10 p-4">
        <div className="mb-3 flex items-center justify-between">
          <button
            type="button"
            aria-label="Mes anterior"
            disabled={mesActual}
            onClick={() => mover(-1)}
            className="flex size-8 items-center justify-center rounded-lg border border-slate-200 dark:border-white/10 text-slate-500 dark:text-white/55 disabled:opacity-30"
          >
            <ChevronLeft className="size-4" />
          </button>
          <span className="text-sm font-bold text-[#0B1B3A] dark:text-[#f4f1e9]">
            {tituloMes}
          </span>
          <button
            type="button"
            aria-label="Mes siguiente"
            onClick={() => mover(1)}
            className="flex size-8 items-center justify-center rounded-lg border border-slate-200 dark:border-white/10 text-slate-500 dark:text-white/55"
          >
            <ChevronRight className="size-4" />
          </button>
        </div>
        <div className="grid grid-cols-7 gap-1 text-center">
          {DIAS.map((d, i) => (
            <span
              key={i}
              className="py-1 text-[10px] font-semibold text-slate-400 dark:text-white/40"
            >
              {d}
            </span>
          ))}
          {celdas.map((d) => {
            const iso = aIso(d)
            const delMes = d.getMonth() === mesVisto.getMonth()
            const pasado = iso < hoy
            const activo = fecha === iso
            return (
              <button
                key={iso}
                type="button"
                aria-label={d.toLocaleDateString('es-CO', {
                  weekday: 'long',
                  day: 'numeric',
                  month: 'long',
                })}
                aria-pressed={activo}
                disabled={pasado || !delMes}
                onClick={() => seleccionarFecha(iso)}
                className={cn(
                  'aspect-square rounded-lg text-xs font-medium text-[#0B1B3A] dark:text-[#f4f1e9] transition-colors hover:bg-slate-100 dark:hover:bg-white/10 disabled:hover:bg-transparent',
                  (pasado || !delMes) && 'text-slate-300 dark:text-white/30',
                  activo &&
                    'bg-[#E5283C] dark:bg-[#d7b36a] font-bold text-white dark:text-[#111411] hover:bg-[#E5283C] dark:hover:bg-[#d7b36a]',
                )}
              >
                {d.getDate()}
              </button>
            )
          })}
        </div>
        {fecha && (
          <p className="mt-3 flex items-center gap-1.5 text-[11px] text-slate-500 dark:text-white/55">
            <span className="size-1.5 rounded-full bg-[#E5283C] dark:bg-[#d7b36a]" />
            Día seleccionado:{' '}
            {fechaLocal(fecha).toLocaleDateString('es-CO', {
              weekday: 'short',
              day: 'numeric',
              month: 'long',
            })}
          </p>
        )}
      </div>

      <div>
        <h3 className="mb-3 text-[11px] font-semibold uppercase tracking-wider text-slate-400 dark:text-white/40">
          Horarios para el {fecha ? diaMes(fecha) : '…'}
        </h3>
        {!franjas ? (
          <p className="text-sm text-slate-500 dark:text-white/55">
            Cargando horarios…
          </p>
        ) : (
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
            {franjas.map((f) => (
              <button
                key={f.hora}
                type="button"
                aria-label={`Hora ${f.hora}${f.disponible ? '' : ' (ocupada)'}`}
                aria-pressed={hora === f.hora}
                disabled={!f.disponible}
                onClick={() => seleccionarHora(f.hora)}
                className={cn(
                  'h-11 rounded-xl border border-slate-200 dark:border-white/10 bg-white dark:bg-[#151915] text-sm font-medium text-[#0B1B3A] dark:text-[#f4f1e9] transition-colors hover:border-slate-300 dark:hover:border-white/20',
                  hora === f.hora &&
                    'border-[#E5283C] dark:border-[#d7b36a] bg-[#FEF2F3] dark:bg-[#d7b36a]/10 text-[#E5283C] dark:text-[#d7b36a] hover:border-[#E5283C] dark:hover:border-[#d7b36a]',
                  !f.disponible &&
                    'cursor-not-allowed border-transparent bg-slate-50 dark:bg-white/5 text-slate-300 dark:text-white/30 hover:border-transparent',
                )}
              >
                {f.hora}
              </button>
            ))}
          </div>
        )}
        <p className="mt-4 text-xs text-slate-400 dark:text-white/40">
          Hora local de Popayán, Colombia
        </p>
      </div>
    </div>
  )
}
