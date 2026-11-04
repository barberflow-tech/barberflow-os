import { Clock, Pencil, Plus, Scissors, Star, Trash2, X } from 'lucide-react'
import { useEffect, useState } from 'react'
import { formatearPrecio } from '@/components/booking/wizard/formato'
import { cn } from '@/lib/utils'
import { useServicesStore, type Service } from '@/stores/useServicesStore'
import { AdminShell } from './AdminShell'

/** Foto del portafolio que todavía no es un servicio del catálogo. */
export interface FotoPendiente {
  id: string
  url: string
  titulo?: string
}

interface ServicesManagerProps {
  /** Fotos listas para convertirse en servicio (nombre, precio, duración y categoría). */
  fotosPendientes?: FotoPendiente[]
  /** Se llama cuando una foto pendiente ya se convirtió en servicio. */
  onFotoUsada?: (id: string) => void
}

type FormularioServicio = Omit<Service, 'id'>

const CATEGORIAS = ['Cortes', 'Barbas', 'Combos', 'Tratamientos']

const vacio: FormularioServicio = {
  name: '',
  description: '',
  duration_minutes: 30,
  price: 0,
  category: 'Cortes',
  is_active: true,
  is_featured: false,
  image_url: '',
}

const campo =
  'w-full rounded-xl border border-app-fg/15 bg-app-fg/5 px-4 py-3 text-sm text-app-fg placeholder:text-app-fg/30 focus:border-brand focus:outline-none'
const etiqueta =
  'mb-1.5 block text-xs font-semibold tracking-wide text-app-fg/60 uppercase'
const botonDorado =
  'inline-flex items-center justify-center gap-2 rounded-full bg-brand px-5 py-2.5 text-sm font-semibold text-brand-fg transition hover:bg-brand-hover'
const botonLinea =
  'inline-flex items-center justify-center gap-2 rounded-full border border-app-fg/15 px-4 py-2 text-sm font-medium text-app-fg/80 transition hover:border-brand/60 hover:text-app-fg'

export function ServicesManager({
  fotosPendientes = [],
  onFotoUsada,
}: ServicesManagerProps) {
  const {
    services,
    isLoading,
    error,
    fetchServices,
    addService,
    updateServiceOptimistic,
    deleteService,
  } = useServicesStore()

  const [filtro, setFiltro] = useState('Todas')
  const [form, setForm] = useState<FormularioServicio>({ ...vacio })
  const [modalAbierto, setModalAbierto] = useState(false)
  const [editando, setEditando] = useState<Service | null>(null)
  const [fotoOrigen, setFotoOrigen] = useState<FotoPendiente | null>(null)
  const [porBorrar, setPorBorrar] = useState<Service | null>(null)
  const [errorForm, setErrorForm] = useState<string | null>(null)
  const [guardando, setGuardando] = useState(false)
  const [errorLista, setErrorLista] = useState<string | null>(null)

  useEffect(() => {
    void fetchServices()
  }, [fetchServices])

  const categorias = [
    'Todas',
    ...new Set([...CATEGORIAS, ...services.map((s) => s.category)]),
    'Destacados',
  ]
  const visibles = services.filter((s) =>
    filtro === 'Todas'
      ? true
      : filtro === 'Destacados'
        ? s.is_featured
        : s.category === filtro,
  )

  const abrirNuevo = (foto?: FotoPendiente) => {
    setEditando(null)
    setFotoOrigen(foto ?? null)
    setForm({ ...vacio, image_url: foto?.url ?? '', name: foto?.titulo ?? '' })
    setErrorForm(null)
    setModalAbierto(true)
  }

  const abrirEdicion = (servicio: Service) => {
    setEditando(servicio)
    setFotoOrigen(null)
    setForm({
      name: servicio.name,
      description: servicio.description,
      duration_minutes: servicio.duration_minutes,
      price: servicio.price,
      category: servicio.category,
      is_active: servicio.is_active,
      is_featured: servicio.is_featured,
      image_url: servicio.image_url,
    })
    setErrorForm(null)
    setModalAbierto(true)
  }

  const cerrarModal = () => {
    setModalAbierto(false)
    setEditando(null)
    setFotoOrigen(null)
  }

  const guardar = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    setGuardando(true)
    setErrorForm(null)
    try {
      if (editando) {
        await updateServiceOptimistic(editando.id, form)
      } else {
        await addService(form)
        if (fotoOrigen) onFotoUsada?.(fotoOrigen.id)
      }
      cerrarModal()
    } catch (err) {
      // El modal queda abierto con lo escrito para poder corregir y reintentar.
      setErrorForm(
        err instanceof Error ? err.message : 'No se pudo guardar el servicio.',
      )
    } finally {
      setGuardando(false)
    }
  }

  const eliminar = async (servicio: Service) => {
    setPorBorrar(null)
    setErrorLista(null)
    try {
      await deleteService(servicio.id)
    } catch (err) {
      setErrorLista(
        err instanceof Error ? err.message : 'No se pudo eliminar el servicio.',
      )
    }
  }

  const cambiar = (
    e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>,
  ) => {
    const { name, type, value } = e.target
    const dato =
      type === 'checkbox'
        ? (e.target as HTMLInputElement).checked
        : type === 'number'
          ? Number(value)
          : value
    setForm((prev) => ({ ...prev, [name]: dato }))
  }

  return (
    <AdminShell>
      <div className="mb-10 flex flex-col justify-between gap-6 sm:flex-row sm:items-end">
        <div>
          <p className="mb-4 flex items-center gap-3 text-xs font-semibold tracking-[0.22em] text-brand uppercase">
            <span className="h-px w-8 bg-brand" />
            Servicios
          </p>
          <h1 className="font-['Playfair_Display',serif] text-4xl leading-tight sm:text-5xl">
            Catálogo de servicios
          </h1>
          <p className="mt-3 max-w-xl text-app-fg/60">
            Lo que tus clientes pueden reservar. Ajusta nombre, precio, duración y
            categoría.
          </p>
        </div>
        <button type="button" onClick={() => abrirNuevo()} className={botonDorado}>
          <Plus className="size-4" aria-hidden="true" />
          Nuevo servicio
        </button>
      </div>

      {fotosPendientes.length > 0 && (
        <section
          aria-label="Fotos del portafolio por configurar"
          className="mb-10 rounded-2xl border border-brand/30 bg-brand/[0.04] p-5"
        >
          <h2 className="font-['Playfair_Display',serif] text-xl">
            Fotos del portafolio por configurar
          </h2>
          <p className="mt-1 text-sm text-app-fg/55">
            Subiste estas fotos en el portafolio. Conviértelas en servicio poniéndoles
            nombre, precio, duración y categoría.
          </p>
          <ul className="mt-5 grid gap-4 sm:grid-cols-3 lg:grid-cols-5">
            {fotosPendientes.map((foto) => (
              <li
                key={foto.id}
                className="overflow-hidden rounded-xl border border-app-fg/10 bg-app"
              >
                <img src={foto.url} alt="" className="h-32 w-full object-cover" />
                <button
                  type="button"
                  onClick={() => abrirNuevo(foto)}
                  className="w-full px-3 py-2.5 text-xs font-semibold text-brand transition hover:bg-app-fg/5"
                >
                  Configurar servicio
                </button>
              </li>
            ))}
          </ul>
        </section>
      )}

      <div
        role="group"
        aria-label="Filtrar por categoría"
        className="mb-8 flex flex-wrap gap-2"
      >
        {categorias.map((categoria) => (
          <button
            key={categoria}
            type="button"
            aria-pressed={filtro === categoria}
            onClick={() => setFiltro(categoria)}
            className={cn(
              'rounded-full border px-4 py-1.5 text-sm transition',
              filtro === categoria
                ? 'border-brand bg-brand font-semibold text-brand-fg'
                : 'border-app-fg/15 text-app-fg/70 hover:border-app-fg/40',
            )}
          >
            {categoria}
          </button>
        ))}
      </div>

      {(error ?? errorLista) && (
        <p role="alert" className="mb-6 text-sm text-red-600 dark:text-red-400">
          {error ?? errorLista}
        </p>
      )}
      {isLoading && services.length === 0 && (
        <p className="text-sm text-app-fg/50">Cargando servicios…</p>
      )}
      {!isLoading && !error && services.length === 0 && (
        <p className="text-sm text-app-fg/50">
          Aún no hay servicios en el catálogo. Crea uno con «Nuevo servicio».
        </p>
      )}

      <ul className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        {visibles.map((servicio) => (
          <li
            key={servicio.id}
            className="flex flex-col overflow-hidden rounded-2xl border border-app-fg/10 bg-app-fg/[0.03] transition hover:border-brand/50"
          >
            <div className="relative h-44 bg-app-fg/5">
              {servicio.image_url ? (
                <img
                  src={servicio.image_url}
                  alt={servicio.name}
                  className="h-full w-full object-cover"
                />
              ) : (
                <div
                  aria-hidden="true"
                  className="grid h-full place-items-center text-app-fg/20"
                >
                  <Scissors className="size-12" />
                </div>
              )}
              <span className="absolute bottom-3 left-3 rounded-full bg-app/85 px-3 py-1 text-[0.65rem] font-semibold tracking-wider text-brand uppercase backdrop-blur">
                {servicio.category}
              </span>
              <button
                type="button"
                aria-label={
                  servicio.is_featured
                    ? `Quitar ${servicio.name} de destacados`
                    : `Destacar ${servicio.name}`
                }
                aria-pressed={servicio.is_featured}
                onClick={() =>
                  void updateServiceOptimistic(servicio.id, {
                    is_featured: !servicio.is_featured,
                  })
                }
                className="absolute top-3 right-3 grid size-9 place-items-center rounded-full bg-app/85 backdrop-blur transition hover:bg-app"
              >
                <Star
                  className={cn(
                    'size-4',
                    servicio.is_featured ? 'fill-brand text-brand' : 'text-app-fg/70',
                  )}
                  aria-hidden="true"
                />
              </button>
            </div>

            <div className="flex flex-1 flex-col gap-3 p-5">
              <h3 className="font-['Playfair_Display',serif] text-xl">
                {servicio.name}
              </h3>
              <p className="flex items-center gap-1.5 text-sm text-app-fg/55">
                <Clock className="size-3.5" aria-hidden="true" />
                {servicio.duration_minutes} min
              </p>
              <div className="mt-auto flex items-center justify-between">
                <span className="text-lg font-semibold text-brand">
                  {formatearPrecio(servicio.price)}
                </span>
                <span
                  className={cn(
                    'rounded-full px-2.5 py-0.5 text-xs font-semibold',
                    servicio.is_active
                      ? 'bg-emerald-500/15 text-emerald-700 dark:text-emerald-300'
                      : 'bg-app-fg/10 text-app-fg/50',
                  )}
                >
                  {servicio.is_active ? 'Activo' : 'Inactivo'}
                </span>
              </div>
              <div className="flex gap-2 border-t border-app-fg/10 pt-4">
                <button
                  type="button"
                  onClick={() => abrirEdicion(servicio)}
                  className={cn(botonLinea, 'flex-1')}
                >
                  <Pencil className="size-3.5" aria-hidden="true" />
                  Editar
                </button>
                <button
                  type="button"
                  aria-label={`Eliminar ${servicio.name}`}
                  onClick={() => setPorBorrar(servicio)}
                  className={cn(
                    botonLinea,
                    'px-3 hover:border-red-400/60 hover:text-red-300',
                  )}
                >
                  <Trash2 className="size-4" aria-hidden="true" />
                </button>
              </div>
            </div>
          </li>
        ))}
      </ul>

      {modalAbierto && (
        <div className="fixed inset-0 z-50 grid place-items-center overflow-y-auto bg-black/70 p-4">
          <form
            role="dialog"
            aria-modal="true"
            aria-label={editando ? 'Editar servicio' : 'Nuevo servicio'}
            onSubmit={(e) => void guardar(e)}
            className="w-full max-w-lg space-y-5 rounded-2xl border border-app-fg/10 bg-panel p-6"
          >
            <div className="flex items-start justify-between">
              <h2 className="font-['Playfair_Display',serif] text-2xl">
                {editando ? 'Editar servicio' : 'Nuevo servicio'}
              </h2>
              <button
                type="button"
                aria-label="Cerrar"
                onClick={cerrarModal}
                className="text-app-fg/50 hover:text-app-fg"
              >
                <X className="size-5" aria-hidden="true" />
              </button>
            </div>

            {form.image_url && (
              <img
                src={form.image_url}
                alt="Vista previa del servicio"
                className="h-40 w-full rounded-xl object-cover"
              />
            )}

            <div>
              <label htmlFor="servicio-nombre" className={etiqueta}>
                Nombre
              </label>
              <input
                id="servicio-nombre"
                name="name"
                required
                value={form.name}
                onChange={cambiar}
                placeholder="Ej. Corte clásico"
                className={campo}
              />
            </div>

            <div>
              <label htmlFor="servicio-descripcion" className={etiqueta}>
                Descripción
              </label>
              <textarea
                id="servicio-descripcion"
                name="description"
                rows={2}
                maxLength={500}
                value={form.description}
                onChange={cambiar}
                placeholder="Qué incluye el servicio"
                className={campo}
              />
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <label htmlFor="servicio-precio" className={etiqueta}>
                  Precio (COP)
                </label>
                <input
                  id="servicio-precio"
                  name="price"
                  type="number"
                  min={0}
                  step={1000}
                  required
                  value={form.price}
                  onChange={cambiar}
                  className={campo}
                />
              </div>
              <div>
                <label htmlFor="servicio-duracion" className={etiqueta}>
                  Duración (min)
                </label>
                <input
                  id="servicio-duracion"
                  name="duration_minutes"
                  type="number"
                  min={5}
                  step={5}
                  required
                  value={form.duration_minutes}
                  onChange={cambiar}
                  className={campo}
                />
              </div>
            </div>

            <div>
              <label htmlFor="servicio-categoria" className={etiqueta}>
                Categoría
              </label>
              <select
                id="servicio-categoria"
                name="category"
                value={form.category}
                onChange={cambiar}
                className={campo}
              >
                {[...new Set([...CATEGORIAS, form.category])].map((c) => (
                  <option key={c} value={c} className="bg-panel">
                    {c}
                  </option>
                ))}
              </select>
            </div>

            <div className="flex flex-wrap gap-6 text-sm text-app-fg/75">
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  name="is_active"
                  checked={form.is_active}
                  onChange={cambiar}
                  className="accent-brand"
                />
                Servicio activo
              </label>
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  name="is_featured"
                  checked={form.is_featured}
                  onChange={cambiar}
                  className="accent-brand"
                />
                Destacado
              </label>
            </div>

            {errorForm && (
              <p role="alert" className="text-sm text-red-600 dark:text-red-400">
                {errorForm}
              </p>
            )}

            <div className="flex justify-end gap-3 pt-2">
              <button type="button" onClick={cerrarModal} className={botonLinea}>
                Cancelar
              </button>
              <button
                type="submit"
                disabled={guardando}
                className={cn(botonDorado, 'disabled:opacity-60')}
              >
                {editando ? 'Guardar cambios' : 'Crear servicio'}
              </button>
            </div>
          </form>
        </div>
      )}

      {porBorrar && (
        <div className="fixed inset-0 z-50 grid place-items-center bg-black/70 p-4">
          <div
            role="alertdialog"
            aria-modal="true"
            aria-label="Eliminar servicio"
            className="w-full max-w-sm space-y-4 rounded-2xl border border-app-fg/10 bg-panel p-6"
          >
            <h2 className="font-['Playfair_Display',serif] text-xl">
              Eliminar servicio
            </h2>
            <p className="text-sm text-app-fg/65">
              ¿Quieres eliminar «{porBorrar.name}» del catálogo?
            </p>
            <div className="flex justify-end gap-3">
              <button
                type="button"
                onClick={() => setPorBorrar(null)}
                className={botonLinea}
              >
                Cancelar
              </button>
              <button
                type="button"
                onClick={() => void eliminar(porBorrar)}
                className="inline-flex items-center rounded-full bg-red-500 px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-red-400"
              >
                Eliminar
              </button>
            </div>
          </div>
        </div>
      )}
    </AdminShell>
  )
}
