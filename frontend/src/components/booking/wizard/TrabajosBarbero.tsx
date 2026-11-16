import { useEffect, useState } from 'react'
import { listarPortafolioPublicoApi, type FotoPublicaApi } from '@/lib/barberosApi'
import type { Barbero, Servicio } from '@/lib/reservaApi'

/** Trabajos reales del barbero elegido en el servicio que está reservando. */
export function TrabajosBarbero({
  barbero,
  servicio,
}: {
  barbero: Barbero
  servicio: Servicio | null
}) {
  const clave = `${barbero.id}-${servicio?.id ?? 'todos'}`
  // Se guarda junto a la consulta que la originó: si cambia el barbero o el
  // servicio, las fotos viejas no se muestran mientras llegan las nuevas.
  const [resultado, setResultado] = useState<{
    clave: string
    fotos: FotoPublicaApi[]
  } | null>(null)

  useEffect(() => {
    let activo = true
    listarPortafolioPublicoApi({ barberoId: barbero.id, servicioId: servicio?.id })
      .then((fotos) => {
        if (activo) setResultado({ clave, fotos })
      })
      .catch(() => {
        // Sin trabajos publicados la reserva sigue funcionando igual.
        if (activo) setResultado({ clave, fotos: [] })
      })
    return () => {
      activo = false
    }
  }, [clave, barbero.id, servicio?.id])

  const fotos = resultado?.clave === clave ? resultado.fotos : []

  // Mientras carga o si no hay fotos, no se muestra nada: no estorba la reserva.
  if (fotos.length === 0) return null

  return (
    <section aria-label={`Trabajos de ${barbero.nombre}`}>
      <h3 className="mb-3 text-sm font-bold text-[#0B1B3A] dark:text-[#f4f1e9]">
        Trabajos de {barbero.nombre}
        {servicio && (
          <span className="font-normal text-slate-500 dark:text-white/55">
            {' '}
            · {servicio.nombre}
          </span>
        )}
      </h3>
      <ul className="grid grid-cols-2 gap-3 sm:grid-cols-3">
        {fotos.map((f) => (
          <li
            key={f.id}
            className="overflow-hidden rounded-xl border border-slate-200 bg-white dark:border-white/10 dark:bg-[#171a18]"
          >
            <img
              src={f.image_url}
              alt={`${f.servicio.name} por ${f.barbero.name}`}
              loading="lazy"
              className="aspect-square w-full object-cover"
            />
            {f.nota && (
              <p className="p-2 text-xs text-slate-600 dark:text-white/65">{f.nota}</p>
            )}
          </li>
        ))}
      </ul>
    </section>
  )
}
