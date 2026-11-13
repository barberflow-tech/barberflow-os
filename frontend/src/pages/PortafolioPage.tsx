import { useEffect, useState } from 'react'
import {
  GaleriaPortafolio,
  type FotoPortafolio,
} from '@/components/portfolio/GaleriaPortafolio'
import {
  listarMisServicios,
  listarPortafolio,
  subirFoto,
  type DatosFoto,
  type FotoApi,
  type ServicioFotoApi,
} from '@/lib/portafolioApi'

const fecha = new Intl.DateTimeFormat('es-CO', { dateStyle: 'long' })
const moneda = new Intl.NumberFormat('es-CO', {
  style: 'currency',
  currency: 'COP',
  maximumFractionDigits: 0,
})

function aFoto(f: FotoApi): FotoPortafolio {
  // Con corte asociado, nombre, precio y descripción vienen del catálogo del admin.
  const s = f.servicio
  const titulo = s?.name ?? (f.original_filename.replace(/\.[^.]+$/, '') || 'Trabajo')
  return {
    id: String(f.id),
    titulo,
    descripcion:
      f.nota ||
      s?.description ||
      `Publicada el ${fecha.format(new Date(f.created_at))}.`,
    url: f.image_url,
    alt: `Fotografía del portafolio: ${titulo}`,
    precio: s ? moneda.format(Number(s.price)) : undefined,
    duracion: s ? `${s.duration_minutes} min` : undefined,
  }
}

export function PortafolioPage() {
  const [fotos, setFotos] = useState<FotoPortafolio[]>([])
  const [cargando, setCargando] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [intento, setIntento] = useState(0)
  const [servicios, setServicios] = useState<ServicioFotoApi[]>([])

  // El catálogo lo gestiona el admin y él asigna a cada barbero sus servicios:
  // aquí solo se leen los del barbero para elegir el corte de cada foto.
  useEffect(() => {
    listarMisServicios()
      .then(setServicios)
      .catch(() => setServicios([]))
  }, [])

  useEffect(() => {
    let vigente = true
    listarPortafolio()
      .then((lista) => {
        if (!vigente) return
        setFotos(lista.map(aFoto))
        setError(null)
      })
      .catch((e: unknown) => {
        if (!vigente) return
        setError(e instanceof Error ? e.message : 'No se pudo cargar el portafolio.')
      })
      .finally(() => {
        if (vigente) setCargando(false)
      })
    return () => {
      vigente = false
    }
  }, [intento])

  function reintentar() {
    setCargando(true)
    setIntento((n) => n + 1)
  }

  async function subir(
    archivo: File,
    onProgress: (pct: number) => void,
    datos: DatosFoto,
  ) {
    const nueva = await subirFoto(archivo, onProgress, datos)
    // Se agrega al inicio sin repetir la petición de la lista completa.
    setFotos((previas) => [aFoto(nueva), ...previas])
  }

  return (
    <GaleriaPortafolio
      fotos={fotos}
      cargando={cargando}
      error={error}
      onReintentar={reintentar}
      servicios={servicios.map((s) => ({
        id: s.id,
        nombre: s.name,
        precio: moneda.format(Number(s.price)),
      }))}
      onUpload={subir}
    />
  )
}

export default PortafolioPage
