import { Check } from 'lucide-react'
import { useEffect, useState } from 'react'
import {
  asignarServiciosApi,
  BarberosError,
  listarBarberosApi,
  type BarberoApi,
} from '@/lib/barberosApi'
import { listarServiciosApi, type ServicioApi } from '@/lib/catalogoApi'
import { AdminShell } from './AdminShell'

const botonDorado =
  'inline-flex items-center justify-center gap-2 rounded-full bg-brand px-5 py-2.5 text-sm font-semibold text-brand-fg transition hover:bg-brand-hover disabled:cursor-not-allowed disabled:opacity-50'

type Estado = 'cargando' | 'listo' | 'error'

/** El admin define qué servicios realiza cada barbero. */
export function BarberosManager() {
  const [barberos, setBarberos] = useState<BarberoApi[]>([])
  const [servicios, setServicios] = useState<ServicioApi[]>([])
  const [estado, setEstado] = useState<Estado>('cargando')
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let vigente = true
    // El admin ve también los servicios inactivos; aquí solo se asignan los activos.
    Promise.all([listarBarberosApi(), listarServiciosApi()])
      .then(([b, s]) => {
        if (!vigente) return
        setBarberos(b)
        setServicios(s.filter((x) => x.is_active))
        setEstado('listo')
      })
      .catch((e: unknown) => {
        if (!vigente) return
        setError(e instanceof Error ? e.message : 'No se pudo cargar la información.')
        setEstado('error')
      })
    return () => {
      vigente = false
    }
  }, [])

  return (
    <AdminShell>
      <p className="mb-4 flex items-center gap-3 text-xs font-semibold tracking-[0.22em] text-brand uppercase">
        <span className="h-px w-8 bg-brand" />
        Equipo
      </p>
      <h1 className="font-['Playfair_Display',serif] text-4xl leading-tight sm:text-5xl">
        Servicios por barbero
      </h1>
      <p className="mt-3 max-w-xl text-app-fg/60">
        Elige qué servicios realiza cada barbero. Solo podrá publicar fotos de esos
        servicios y los clientes solo lo verán al reservarlos.
      </p>

      {estado === 'cargando' && (
        <p role="status" className="mt-12 text-app-fg/60">
          Cargando barberos…
        </p>
      )}
      {estado === 'error' && (
        <p role="alert" className="mt-12 text-sm text-red-400">
          {error}
        </p>
      )}
      {estado === 'listo' && barberos.length === 0 && (
        <p className="mt-12 text-app-fg/60">Aún no hay barberos registrados.</p>
      )}
      {estado === 'listo' && servicios.length === 0 && barberos.length > 0 && (
        <p className="mt-12 text-app-fg/60">
          Primero crea servicios en el catálogo para poder asignarlos.
        </p>
      )}

      {estado === 'listo' && servicios.length > 0 && (
        <ul className="mt-10 grid gap-5 lg:grid-cols-2">
          {barberos.map((b) => (
            <li key={b.id}>
              <TarjetaBarbero barbero={b} servicios={servicios} />
            </li>
          ))}
        </ul>
      )}
    </AdminShell>
  )
}

function TarjetaBarbero({
  barbero,
  servicios,
}: {
  barbero: BarberoApi
  servicios: ServicioApi[]
}) {
  const [elegidos, setElegidos] = useState<Set<number>>(new Set(barbero.servicios))
  const [guardado, setGuardado] = useState(new Set(barbero.servicios))
  const [guardando, setGuardando] = useState(false)
  const [mensaje, setMensaje] = useState<{ texto: string; ok: boolean } | null>(null)

  const cambios =
    elegidos.size !== guardado.size || [...elegidos].some((id) => !guardado.has(id))

  function alternar(id: number) {
    setMensaje(null)
    setElegidos((previos) => {
      const siguiente = new Set(previos)
      if (!siguiente.delete(id)) siguiente.add(id)
      return siguiente
    })
  }

  async function guardar() {
    setGuardando(true)
    setMensaje(null)
    try {
      const actualizado = await asignarServiciosApi(barbero.id, [...elegidos])
      setGuardado(new Set(actualizado.servicios))
      setMensaje({ texto: 'Guardado', ok: true })
    } catch (e) {
      setMensaje({
        texto: e instanceof BarberosError ? e.message : 'No se pudo guardar.',
        ok: false,
      })
    } finally {
      setGuardando(false)
    }
  }

  return (
    <section
      aria-label={`Servicios de ${barbero.name}`}
      className="rounded-2xl border border-app-fg/10 bg-app-fg/[0.03] p-6"
    >
      <h2 className="font-['Playfair_Display',serif] text-2xl">{barbero.name}</h2>
      <p className="mt-1 text-xs text-app-fg/50">
        {elegidos.size} {elegidos.size === 1 ? 'servicio' : 'servicios'} asignados
      </p>

      <ul className="mt-4 space-y-2">
        {servicios.map((s) => (
          <li key={s.id}>
            <label className="flex cursor-pointer items-center gap-3 rounded-xl border border-app-fg/10 px-4 py-3 text-sm transition hover:border-brand/50">
              <input
                type="checkbox"
                checked={elegidos.has(s.id)}
                onChange={() => alternar(s.id)}
                className="size-4 accent-[var(--color-brand,#d7b36a)]"
              />
              <span className="flex-1">{s.name}</span>
              <span className="text-app-fg/50">{s.duration_minutes} min</span>
            </label>
          </li>
        ))}
      </ul>

      <div className="mt-5 flex items-center gap-4">
        <button
          type="button"
          disabled={!cambios || guardando}
          onClick={() => void guardar()}
          className={botonDorado}
        >
          {guardando ? 'Guardando…' : 'Guardar cambios'}
        </button>
        {mensaje && (
          <p
            role={mensaje.ok ? 'status' : 'alert'}
            className={
              mensaje.ok
                ? 'flex items-center gap-1 text-sm text-emerald-400'
                : 'text-sm text-red-400'
            }
          >
            {mensaje.ok && <Check className="size-4" aria-hidden="true" />}
            {mensaje.texto}
          </p>
        )}
      </div>
    </section>
  )
}

export default BarberosManager
