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
      <div className="rounded-2xl border border-slate-200 p-4">
        <div className="mb-3 flex items-center justify-between">
          <button
            type="button"
            aria-label="Mes anterior"
            disabled={mesActual}
            onClick={() => mover(-1)}
            className="flex size-8 items-center justify-center rounded-lg border border-slate-200 text-slate-500 disabled:opacity-30"
          >
            <ChevronLeft className="size-4" />
          </button>
          <span className="text-sm font-bold text-[#0B1B3A]">{tituloMes}</span>
          <button
            type="button"
            aria-label="Mes siguiente"
            onClick={() => mover(1)}
            className="flex size-8 items-center justify-center rounded-lg border border-slate-200 text-slate-500"
          >
            <ChevronRight className="size-4" />
          </button>
        </div>
        <div className="grid grid-cols-7 gap-1 text-center">
          {DIAS.map((d, i) => (
            <span key={i} className="py-1 text-[10px] font-semibold text-slate-400">
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
                  'aspect-square rounded-lg text-xs font-medium text-[#0B1B3A] transition-colors hover:bg-slate-100 disabled:hover:bg-transparent',
                  (pasado || !delMes) && 'text-slate-300',
                  activo && 'bg-[#E5283C] font-bold text-white hover:bg-[#E5283C]',
                )}
              >
                {d.getDate()}
              </button>
            )
          })}
        </div>
        {fecha && (
          <p className="mt-3 flex items-center gap-1.5 text-[11px] text-slate-500">
            <span className="size-1.5 rounded-full bg-[#E5283C]" />
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
        <h3 className="mb-3 text-[11px] font-semibold uppercase tracking-wider text-slate-400">
          Horarios para el {fecha ? diaMes(fecha) : '…'}
        </h3>
        {!franjas ? (
          <p className="text-sm text-slate-500">Cargando horarios…</p>
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
                  'h-11 rounded-xl border border-slate-200 bg-white text-sm font-medium text-[#0B1B3A] transition-colors hover:border-slate-300',
                  hora === f.hora &&
                    'border-[#E5283C] bg-[#FEF2F3] text-[#E5283C] hover:border-[#E5283C]',
                  !f.disponible &&
                    'cursor-not-allowed border-transparent bg-slate-50 text-slate-300 hover:border-transparent',
                )}
              >
                {f.hora}
              </button>
            ))}
          </div>
        )}
        <p className="mt-4 text-xs text-slate-400">Hora local de Popayán, Colombia</p>
      </div>
    </div>
  )
}
