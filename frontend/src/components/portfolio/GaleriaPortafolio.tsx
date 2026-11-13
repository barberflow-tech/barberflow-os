import '@fontsource/dm-sans/400.css'
import '@fontsource/dm-sans/500.css'
import '@fontsource/dm-sans/600.css'
import '@fontsource/playfair-display/400.css'
import '@fontsource/playfair-display/400-italic.css'
import { ChevronLeft, ChevronRight, Plus, X } from 'lucide-react'
import { useEffect, useState } from 'react'
import { cn } from '@/lib/utils'
import { useAuthStore } from '@/stores/useAuthStore'
import { Dropzone } from './Dropzone'

export interface FotoPortafolio {
  id: string
  titulo: string
  descripcion: string
  url: string
  alt: string
  /** Precio y duración los define el administrador en el catálogo. */
  precio?: string
  duracion?: string
}

export interface ServicioOpcion {
  id: number
  nombre: string
  precio: string
}

interface GaleriaPortafolioProps {
  fotos: FotoPortafolio[]
  cargando?: boolean
  error?: string | null
  onReintentar?: () => void
  servicios?: ServicioOpcion[]
  onUpload: (
    archivo: File,
    onProgress: (pct: number) => void,
    datos: { servicioId: number; nota: string },
  ) => Promise<void>
}

export function GaleriaPortafolio({
  fotos,
  cargando = false,
  error = null,
  onReintentar,
  servicios = [],
  onUpload,
}: GaleriaPortafolioProps) {
  const [actual, setActual] = useState(0)
  const [abierto, setAbierto] = useState(false)
  const logout = useAuthStore((state) => state.logout)
  const foto = fotos[Math.min(actual, fotos.length - 1)]
  const mover = (d: number) => setActual((i) => (i + d + fotos.length) % fotos.length)

  return (
    <main className="min-h-screen overflow-hidden bg-[#0f1210] font-['DM_Sans',sans-serif] text-[#f4f1e9]">
      <header className="border-b border-white/10">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-5 py-5 sm:px-8 lg:px-12">
          <div className="flex items-center gap-3">
            <div className="grid size-10 place-items-center rounded-full border border-[#d7b36a]/50 text-[#d7b36a]">
              <span className="font-['Playfair_Display',serif] text-lg">BF</span>
            </div>
            <div>
              <p className="text-sm font-semibold tracking-[0.08em] text-white">
                BARBERFLOW
              </p>
              <p className="text-[0.65rem] tracking-[0.22em] text-white/45 uppercase">
                OS · Cali
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2 sm:gap-3">
            <button
              type="button"
              onClick={() => void logout()}
              className="rounded-full border border-white/15 px-3 py-2.5 text-sm font-medium whitespace-nowrap text-white/75 sm:px-4 sm:py-3 transition hover:border-[#d7b36a]/60 hover:text-white"
            >
              Cerrar sesión
            </button>
            <button
              type="button"
              onClick={() => setAbierto(true)}
              className="inline-flex items-center gap-2 rounded-full bg-[#d7b36a] px-5 py-3 text-sm font-semibold text-[#111411] transition hover:bg-[#e5c77f]"
            >
              <Plus className="size-4" aria-hidden="true" />
              <span className="hidden sm:inline">Subir fotografía</span>
              <span className="sm:hidden">Subir</span>
            </button>
          </div>
        </div>
      </header>

      <div className="mx-auto max-w-7xl px-5 py-12 sm:px-8 sm:py-16 lg:px-12 lg:py-20">
        <div className="mb-10 flex flex-col justify-between gap-6 sm:flex-row sm:items-end">
          <div>
            <p className="mb-4 flex items-center gap-3 text-xs font-semibold tracking-[0.22em] text-[#d7b36a] uppercase">
              <span className="h-px w-8 bg-[#d7b36a]" />
              Portafolio
            </p>
            <h1 className="max-w-2xl font-['Playfair_Display',serif] text-5xl leading-[0.95] tracking-[-0.03em] text-[#f7f3ea] sm:text-7xl">
              El arte está en <span className="text-[#d7b36a] italic">el detalle.</span>
            </h1>
          </div>
          <div className="max-w-xs border-l border-white/15 pl-5">
            <p className="text-sm leading-6 text-white/55">
              Una selección de cortes, texturas y acabados creados por nuestro equipo en
              Cali.
            </p>
            <p className="mt-3 text-xs font-medium tracking-[0.14em] text-white/40 uppercase">
              {fotos.length} {fotos.length === 1 ? 'fotografía' : 'fotografías'}
            </p>
          </div>
        </div>

        {cargando && (
          <p role="status" className="py-20 text-center text-white/60">
            Cargando tu portafolio...
          </p>
        )}

        {!cargando && error && (
          <div
            role="alert"
            className="flex flex-col items-center gap-4 rounded-[2rem] border border-red-500/30 bg-red-500/10 px-6 py-14 text-center"
          >
            <p className="text-sm text-red-200">{error}</p>
            {onReintentar && (
              <button
                type="button"
                onClick={onReintentar}
                className="rounded-full border border-white/20 px-5 py-2 text-sm font-semibold text-white transition hover:border-[#d7b36a]"
              >
                Reintentar
              </button>
            )}
          </div>
        )}

        {!cargando && !error && !foto && (
          <div className="flex flex-col items-center gap-4 rounded-[2rem] border border-dashed border-white/20 px-6 py-20 text-center">
            <p className="font-['Playfair_Display',serif] text-3xl text-white">
              Aún no tienes fotografías
            </p>
            <p className="max-w-sm text-sm text-white/55">
              Sube tus mejores cortes para que tus clientes vean tu trabajo.
            </p>
            <button
              type="button"
              onClick={() => setAbierto(true)}
              className="rounded-full bg-[#d7b36a] px-6 py-3 text-sm font-semibold text-[#111411] transition hover:bg-[#e5c77f]"
            >
              Subir mi primera fotografía
            </button>
          </div>
        )}

        {foto && (
          <section
            aria-label="Carrusel de fotografías"
            className="grid items-start gap-6 xl:grid-cols-[minmax(0,1fr)_20rem]"
          >
            <div className="group relative w-full self-start overflow-hidden rounded-[2rem] border border-white/10 bg-[#171a18]">
              <div className="relative aspect-[4/3] w-full overflow-hidden sm:aspect-[16/10] lg:aspect-[16/9]">
                <img
                  src={foto.url}
                  alt={foto.alt}
                  className="absolute inset-0 size-full object-cover"
                />
                <div className="absolute inset-0 bg-gradient-to-t from-black/85 via-transparent to-black/10" />
                <div className="absolute inset-x-0 bottom-0 flex items-end justify-between gap-6 p-6 sm:p-9">
                  <div>
                    <p className="mb-2 text-xs font-semibold tracking-[0.2em] text-[#d7b36a] uppercase">
                      Trabajo destacado
                    </p>
                    <h2 className="font-['Playfair_Display',serif] text-3xl text-white sm:text-5xl">
                      {foto.titulo}
                    </h2>
                    {foto.precio && (
                      <p className="mt-2 text-lg font-semibold text-[#d7b36a]">
                        {foto.precio}
                        {foto.duracion && (
                          <span className="ml-2 text-sm font-normal text-white/60">
                            · {foto.duracion}
                          </span>
                        )}
                      </p>
                    )}
                    <p className="mt-2 max-w-xl text-sm text-white/70">
                      {foto.descripcion}
                    </p>
                  </div>
                  <p className="hidden shrink-0 text-sm text-white/70 tabular-nums sm:block">
                    {String(actual + 1).padStart(2, '0')} /{' '}
                    {String(fotos.length).padStart(2, '0')}
                  </p>
                </div>
              </div>
              {(['Fotografía anterior', 'Fotografía siguiente'] as const).map(
                (label, i) => {
                  const Icono = i === 0 ? ChevronLeft : ChevronRight
                  return (
                    <button
                      key={label}
                      type="button"
                      aria-label={label}
                      onClick={() => mover(i === 0 ? -1 : 1)}
                      className={cn(
                        'absolute top-1/2 grid size-12 -translate-y-1/2 place-items-center rounded-full border border-white/20 bg-black/40 text-white backdrop-blur-md transition hover:bg-[#d7b36a] hover:text-[#111411]',
                        i === 0 ? 'left-4' : 'right-4',
                      )}
                    >
                      <Icono className="size-5" aria-hidden="true" />
                    </button>
                  )
                },
              )}
            </div>

            <div
              aria-label="Miniaturas"
              className="grid grid-cols-2 content-start gap-3 sm:grid-cols-3 xl:grid-cols-2"
            >
              {fotos.map((f, i) => (
                <button
                  key={f.id}
                  type="button"
                  aria-label={`Ver ${f.titulo}`}
                  aria-pressed={i === actual}
                  onClick={() => setActual(i)}
                  className={cn(
                    'min-w-0 overflow-hidden rounded-2xl border text-left transition',
                    i === actual
                      ? 'border-[#d7b36a] ring-1 ring-[#d7b36a]'
                      : 'border-white/10 hover:border-white/40',
                  )}
                >
                  <div className="relative aspect-[16/9] w-full overflow-hidden">
                    <img src={f.url} alt="" className="size-full object-cover" />
                    <span className="absolute inset-0 bg-black/10" />
                  </div>
                  <span className="block bg-[#171a18] p-3">
                    <span className="block text-xs font-semibold text-white">
                      {f.titulo}
                      {f.precio && (
                        <span className="ml-2 font-medium text-[#d7b36a]">
                          {f.precio}
                        </span>
                      )}
                    </span>
                    <span className="mt-1 block text-[0.68rem] leading-4 text-white/50">
                      {f.descripcion}
                    </span>
                  </span>
                </button>
              ))}
            </div>
          </section>
        )}
      </div>

      {abierto && (
        <DialogoSubida
          onCerrar={() => setAbierto(false)}
          servicios={servicios}
          onUpload={onUpload}
        />
      )}
    </main>
  )
}

function DialogoSubida({
  onCerrar,
  servicios,
  onUpload,
}: {
  onCerrar: () => void
  servicios: ServicioOpcion[]
  onUpload: GaleriaPortafolioProps['onUpload']
}) {
  const [servicioId, setServicioId] = useState<number | undefined>(undefined)
  const [nota, setNota] = useState('')
  useEffect(() => {
    const alTeclear = (e: KeyboardEvent) => e.key === 'Escape' && onCerrar()
    document.addEventListener('keydown', alTeclear)
    return () => document.removeEventListener('keydown', alTeclear)
  }, [onCerrar])

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="subida-titulo"
      className="fixed inset-0 z-50 flex items-end justify-center bg-[#0a0c0b]/80 backdrop-blur-sm sm:items-center sm:p-6"
    >
      <div className="max-h-[94vh] w-full overflow-y-auto rounded-t-[2rem] border border-white/10 bg-[#171a18] shadow-2xl sm:max-w-2xl sm:rounded-[2rem]">
        <div className="flex items-start justify-between border-b border-white/10 px-6 py-6 sm:px-8">
          <div>
            <p className="mb-2 text-xs font-semibold tracking-[0.2em] text-[#d7b36a] uppercase">
              Portafolio
            </p>
            <h2
              id="subida-titulo"
              className="font-['Playfair_Display',serif] text-3xl text-white"
            >
              Publica tu trabajo
            </h2>
            <p className="mt-2 text-sm text-white/55">
              Selecciona una o varias fotografías para añadirlas a tu portafolio.
            </p>
          </div>
          <button
            type="button"
            aria-label="Cerrar"
            onClick={onCerrar}
            className="grid size-10 shrink-0 place-items-center rounded-full border border-white/15 text-white/70 transition hover:border-white/40 hover:text-white"
          >
            <X className="size-4" aria-hidden="true" />
          </button>
        </div>
        <div className="space-y-5 px-6 py-6 sm:px-8">
          {servicios.length === 0 ? (
            <p
              role="status"
              className="rounded-2xl border border-white/10 bg-[#0f1210] p-5 text-sm text-white/70"
            >
              El administrador aún no te asignó servicios. Cuando lo haga podrás
              publicar fotos de esos cortes.
            </p>
          ) : (
            <>
              <div>
                <label
                  htmlFor="servicio-foto"
                  className="mb-2 block text-xs font-semibold tracking-[0.14em] text-white/60 uppercase"
                >
                  ¿Qué corte muestra la foto?
                </label>
                <select
                  id="servicio-foto"
                  value={servicioId ?? ''}
                  onChange={(e) =>
                    setServicioId(e.target.value ? Number(e.target.value) : undefined)
                  }
                  className="w-full rounded-xl border border-white/15 bg-[#0f1210] px-4 py-3 text-sm text-white outline-none focus:border-[#d7b36a]"
                >
                  <option value="">Elige un corte…</option>
                  {servicios.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.nombre} · {s.precio}
                    </option>
                  ))}
                </select>
                <p className="mt-2 text-xs text-white/40">
                  El precio y la descripción los define el administrador en el catálogo.
                </p>
              </div>
              {servicioId !== undefined && (
                <>
                  <div>
                    <label
                      htmlFor="nota-foto"
                      className="mb-2 block text-xs font-semibold tracking-[0.14em] text-white/60 uppercase"
                    >
                      Nota (opcional)
                    </label>
                    <input
                      id="nota-foto"
                      type="text"
                      maxLength={200}
                      value={nota}
                      onChange={(e) => setNota(e.target.value)}
                      placeholder="Ej.: degradado bajo con textura arriba"
                      className="w-full rounded-xl border border-white/15 bg-[#0f1210] px-4 py-3 text-sm text-white outline-none placeholder:text-white/30 focus:border-[#d7b36a]"
                    />
                  </div>
                  <Dropzone
                    onUpload={(archivo, onProgress) =>
                      onUpload(archivo, onProgress, { servicioId, nota: nota.trim() })
                    }
                    onTerminado={onCerrar}
                  />
                </>
              )}
            </>
          )}
          <p className="text-xs text-white/40">
            Las fotos se optimizan y se guardan de forma segura en tu portafolio.
          </p>
        </div>
      </div>
    </div>
  )
}
