import { AlertCircle, Check, ImageUp, Upload, X } from 'lucide-react'
import { useEffect, useRef, useState, type DragEvent } from 'react'
import { formatearTamano, TIPOS_PERMITIDOS, validarImagen } from '@/lib/imagenes'
import { cn } from '@/lib/utils'

type Estado = 'lista' | 'subiendo' | 'subida' | 'error'

interface Foto {
  id: number
  archivo: File
  url: string
  estado: Estado
  progreso: number
  error?: string
}

export interface DropzoneProps {
  /** Sube una foto y reporta el avance (0-100). Debe rechazar la promesa si falla. */
  onUpload: (archivo: File, onProgress: (pct: number) => void) => Promise<void>
  /** Se llama cuando todas las fotos pendientes se subieron sin errores. */
  onTerminado?: () => void
}

export function Dropzone({ onUpload, onTerminado }: DropzoneProps) {
  const [fotos, setFotos] = useState<Foto[]>([])
  const [avisos, setAvisos] = useState<string[]>([])
  const [arrastrando, setArrastrando] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)
  const siguienteId = useRef(0)
  const fotosRef = useRef<Foto[]>([])

  useEffect(() => {
    fotosRef.current = fotos
  }, [fotos])

  // Libera las pre-visualizaciones al desmontar.
  useEffect(() => {
    return () => fotosRef.current.forEach((f) => URL.revokeObjectURL(f.url))
  }, [])

  function agregar(lista: FileList | File[]) {
    const nuevas: Foto[] = []
    const rechazos: string[] = []
    for (const archivo of Array.from(lista)) {
      const motivo = validarImagen(archivo)
      if (motivo) {
        rechazos.push(`${archivo.name}: ${motivo}`)
      } else {
        nuevas.push({
          id: siguienteId.current++,
          archivo,
          url: URL.createObjectURL(archivo),
          estado: 'lista',
          progreso: 0,
        })
      }
    }
    setAvisos(rechazos)
    if (nuevas.length) setFotos((prev) => [...prev, ...nuevas])
  }

  function alSoltar(e: DragEvent<HTMLDivElement>) {
    e.preventDefault()
    setArrastrando(false)
    agregar(e.dataTransfer.files)
  }

  function quitar(foto: Foto) {
    URL.revokeObjectURL(foto.url)
    setFotos((prev) => prev.filter((f) => f.id !== foto.id))
  }

  const actualizar = (id: number, cambios: Partial<Foto>) =>
    setFotos((prev) => prev.map((f) => (f.id === id ? { ...f, ...cambios } : f)))

  async function subirUna(foto: Foto): Promise<boolean> {
    actualizar(foto.id, { estado: 'subiendo', progreso: 0, error: undefined })
    try {
      await onUpload(foto.archivo, (pct) =>
        actualizar(foto.id, { progreso: Math.min(100, Math.max(0, Math.round(pct))) }),
      )
      actualizar(foto.id, { estado: 'subida', progreso: 100 })
      return true
    } catch (e) {
      actualizar(foto.id, {
        estado: 'error',
        error: e instanceof Error ? e.message : 'No se pudo subir la foto.',
      })
      return false
    }
  }

  async function subirTodas() {
    const resultados = await Promise.all(pendientes.map(subirUna))
    if (resultados.every(Boolean)) onTerminado?.()
  }

  const pendientes = fotos.filter((f) => f.estado === 'lista' || f.estado === 'error')
  const subiendo = fotos.some((f) => f.estado === 'subiendo')

  return (
    <div className="space-y-4 text-white">
      <div
        data-testid="dropzone"
        onDragOver={(e) => {
          e.preventDefault()
          setArrastrando(true)
        }}
        onDragLeave={(e) => {
          if (!e.currentTarget.contains(e.relatedTarget as Node | null)) {
            setArrastrando(false)
          }
        }}
        onDrop={alSoltar}
        className={cn(
          'flex flex-col items-center justify-center gap-2 rounded-3xl border border-dashed border-white/20 p-8 sm:p-12 hover:border-[#d7b36a]/60 bg-[#0f1210] text-center transition-colors',
          arrastrando && 'border-[#d7b36a] bg-[#d7b36a]/5',
        )}
      >
        <span
          aria-hidden="true"
          className="mb-1 flex size-12 items-center justify-center rounded-full bg-white/[0.06] text-[#d7b36a]"
        >
          <ImageUp className="size-5" />
        </span>
        <p className="text-sm font-semibold">
          Arrastra tus fotos aquí o selecciona archivos
        </p>
        <p className="text-xs text-white/40">JPG, PNG o WebP · Tamaño máximo: 5 MB</p>
        <button
          type="button"
          onClick={() => inputRef.current?.click()}
          className="mt-3 rounded-full border border-white/20 px-5 py-2 text-xs font-semibold transition-colors hover:border-[#d7b36a] hover:text-[#d7b36a]"
        >
          Seleccionar imagen
        </button>
        <input
          ref={inputRef}
          type="file"
          multiple
          accept={TIPOS_PERMITIDOS.join(',')}
          aria-label="Seleccionar imagen"
          tabIndex={-1}
          className="sr-only"
          onChange={(e) => {
            if (e.target.files) agregar(e.target.files)
            e.target.value = ''
          }}
        />
      </div>

      {avisos.length > 0 && (
        <div
          role="alert"
          className="flex gap-2 rounded-xl border border-red-500/30 bg-red-500/10 p-3 text-xs text-red-300"
        >
          <AlertCircle className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
          <ul className="space-y-1">
            {avisos.map((a) => (
              <li key={a}>{a}</li>
            ))}
          </ul>
        </div>
      )}

      {fotos.length > 0 && (
        <ul className="grid gap-2 sm:grid-cols-2">
          {fotos.map((f) => (
            <li
              key={f.id}
              className="flex items-center gap-3 rounded-xl border border-white/10 bg-[#0f1210] p-2"
            >
              <img
                src={f.url}
                alt={`Pre-visualización de ${f.archivo.name}`}
                className="size-14 shrink-0 rounded-lg object-cover"
              />
              <div className="min-w-0 flex-1 space-y-1">
                <p className="truncate text-xs font-semibold">{f.archivo.name}</p>
                <p className="text-[11px] text-white/50">
                  {formatearTamano(f.archivo.size)}
                </p>
                {f.estado === 'subiendo' && (
                  <div
                    role="progressbar"
                    aria-label={`Progreso de ${f.archivo.name}`}
                    aria-valuemin={0}
                    aria-valuemax={100}
                    aria-valuenow={f.progreso}
                    className="h-1.5 overflow-hidden rounded-full bg-white/10"
                  >
                    <div
                      className="h-full rounded-full bg-[#d7b36a] transition-[width]"
                      style={{ width: `${f.progreso}%` }}
                    />
                  </div>
                )}
                {f.estado === 'subida' && (
                  <p className="flex items-center gap-1 text-[11px] text-emerald-400">
                    <Check className="size-3" aria-hidden="true" /> Subida
                  </p>
                )}
                {f.estado === 'error' && (
                  <p className="text-[11px] text-red-300">{f.error}</p>
                )}
              </div>
              <button
                type="button"
                aria-label={`Quitar ${f.archivo.name}`}
                disabled={f.estado === 'subiendo'}
                onClick={() => quitar(f)}
                className="flex size-7 shrink-0 items-center justify-center rounded-full text-white/50 transition-colors hover:bg-white/10 hover:text-white disabled:opacity-30"
              >
                <X className="size-4" aria-hidden="true" />
              </button>
            </li>
          ))}
        </ul>
      )}

      {pendientes.length > 0 && (
        <button
          type="button"
          disabled={subiendo}
          onClick={() => void subirTodas()}
          className="flex h-11 w-full items-center justify-center gap-2 rounded-full bg-[#d7b36a] px-5 text-sm font-semibold text-[#0f1210] transition-colors hover:bg-[#e5c77f] disabled:cursor-not-allowed disabled:opacity-50"
        >
          <Upload className="size-4" aria-hidden="true" />
          Subir {pendientes.length} {pendientes.length === 1 ? 'foto' : 'fotos'}
        </button>
      )}
    </div>
  )
}
