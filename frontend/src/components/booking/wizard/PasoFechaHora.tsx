import { ChevronLeft, ChevronRight } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { SelectorFranjas } from '@/components/booking/SelectorFranjas'
import { atiendeEl, primerDiaLaboral } from '@/lib/diasLaborales'
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
  const servicio = useReservaWizardStore((s) => s.servicio)
  const barbero = useReservaWizardStore((s) => s.barbero)
  const fecha = useReservaWizardStore((s) => s.fecha)
  const hora = useReservaWizardStore((s) => s.hora)
  const seleccionarFecha = useReservaWizardStore((s) => s.seleccionarFecha)
  const seleccionarHora = useReservaWizardStore((s) => s.seleccionarHora)
  const hoy = useMemo(() => aIso(new Date()), [])
  const [mesVisto, setMesVisto] = useState(() => {
    const base = fechaLocal(fecha ?? hoy)
    return new Date(base.getFullYear(), base.getMonth(), 1)
  })

  // Días que atiende el barbero según el horario que configuró el administrador.
  const diasLaborales = barbero?.diasLaborales
  const sinHorario = diasLaborales !== undefined && diasLaborales.length === 0

  // Empieza en el primer día en que sí atiende (hoy puede ser su día libre).
  useEffect(() => {
    if (fecha) return
    const primero = primerDiaLaboral(hoy, diasLaborales)
    if (primero) seleccionarFecha(primero)
  }, [fecha, hoy, diasLaborales, seleccionarFecha])

  const diaCerrado = !!fecha && !atiendeEl(diasLaborales, fecha)
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
      <div className="rounded-2xl border border-[#101820]/12 bg-[#F7F1E8] p-4 dark:border-[#F7F1E8]/12 dark:bg-[#101820]/40">
        <div className="mb-3 flex items-center justify-between">
          <button
            type="button"
            aria-label="Mes anterior"
            disabled={mesActual}
            onClick={() => mover(-1)}
            className="flex size-8 items-center justify-center rounded-lg border border-[#101820]/15 text-[#101820]/60 transition-colors hover:border-[#B3263B] hover:text-[#B3263B] disabled:opacity-30 dark:border-[#F7F1E8]/15 dark:text-[#F7F1E8]/60 dark:hover:border-[#E5283C] dark:hover:text-[#E5283C]"
          >
            <ChevronLeft className="size-4" />
          </button>
          <span className="font-[Barlow_Condensed] text-base font-bold tracking-wide text-[#101820] uppercase dark:text-[#F7F1E8]">
            {tituloMes}
          </span>
          <button
            type="button"
            aria-label="Mes siguiente"
            onClick={() => mover(1)}
            className="flex size-8 items-center justify-center rounded-lg border border-[#101820]/15 text-[#101820]/60 transition-colors hover:border-[#B3263B] hover:text-[#B3263B] dark:border-[#F7F1E8]/15 dark:text-[#F7F1E8]/60 dark:hover:border-[#E5283C] dark:hover:text-[#E5283C]"
          >
            <ChevronRight className="size-4" />
          </button>
        </div>
        <div className="grid grid-cols-7 gap-1 text-center">
          {DIAS.map((d, i) => (
            <span
              key={i}
              className="py-1 text-[10px] font-semibold text-[#101820]/45 dark:text-[#F7F1E8]/45"
            >
              {d}
            </span>
          ))}
          {celdas.map((d) => {
            const iso = aIso(d)
            const delMes = d.getMonth() === mesVisto.getMonth()
            const pasado = iso < hoy
            const cerrado = !atiendeEl(diasLaborales, iso)
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
                disabled={pasado || !delMes || cerrado}
                onClick={() => seleccionarFecha(iso)}
                className={cn(
                  'aspect-square rounded-lg text-xs font-medium text-[#101820] transition-colors hover:bg-[#101820]/8 disabled:hover:bg-transparent dark:text-[#F7F1E8] dark:hover:bg-[#F7F1E8]/10',
                  (pasado || !delMes || cerrado) &&
                    'text-[#101820]/25 dark:text-[#F7F1E8]/25',
                  cerrado && delMes && !pasado && 'line-through',
                  activo &&
                    'bg-[#B3263B] font-bold text-[#F7F1E8] hover:bg-[#B3263B] dark:bg-[#E5283C] dark:text-[#101820] dark:hover:bg-[#E5283C]',
                )}
              >
                {d.getDate()}
              </button>
            )
          })}
        </div>
        {diasLaborales && diasLaborales.length > 0 && diasLaborales.length < 7 && (
          <p className="mt-3 text-[11px] text-[#101820]/50 dark:text-[#F7F1E8]/50">
            Los días tachados {barbero?.nombre} no atiende.
          </p>
        )}
        {fecha && (
          <p className="mt-3 flex items-center gap-1.5 text-[11px] text-[#101820]/65 dark:text-[#F7F1E8]/65">
            <span className="size-1.5 rounded-full bg-[#B3263B] dark:bg-[#E5283C]" />
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
        <h3 className="mb-3 text-[11px] font-semibold tracking-wider text-[#174A7E] uppercase dark:text-[#5FA3E0]">
          Horarios para el {fecha ? diaMes(fecha) : '…'}
        </h3>
        {sinHorario ? (
          <p role="status" className="text-sm text-[#101820]/60 dark:text-[#F7F1E8]/60">
            {barbero?.nombre} aún no tiene un horario configurado. Elige otro barbero.
          </p>
        ) : diaCerrado ? (
          <p className="text-sm text-[#101820]/60 dark:text-[#F7F1E8]/60">
            {barbero?.nombre} no atiende este día. Elige otra fecha.
          </p>
        ) : barbero && fecha ? (
          <SelectorFranjas
            barberoId={barbero.id}
            fecha={fecha}
            duracionMin={servicio?.duracionMin}
            hora={hora}
            onElegir={seleccionarHora}
          />
        ) : null}
        <p className="mt-4 text-xs text-[#101820]/50 dark:text-[#F7F1E8]/50">
          Hora local de Popayán, Colombia
        </p>
      </div>
    </div>
  )
}
