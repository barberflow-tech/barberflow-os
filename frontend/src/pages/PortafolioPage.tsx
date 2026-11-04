import { useEffect, useState } from 'react'
import {
  GaleriaPortafolio,
  type FotoPortafolio,
} from '@/components/portfolio/GaleriaPortafolio'
import { listarPortafolio, subirFoto, type FotoApi } from '@/lib/portafolioApi'

const fecha = new Intl.DateTimeFormat('es-CO', { dateStyle: 'long' })

function aFoto(f: FotoApi): FotoPortafolio {
  const titulo = f.original_filename.replace(/\.[^.]+$/, '') || 'Trabajo'
  return {
    id: String(f.id),
    titulo,
    descripcion: `Publicada el ${fecha.format(new Date(f.created_at))}.`,
    url: f.image_url,
    alt: `Fotografía del portafolio: ${titulo}`,
  }
}

export function PortafolioPage() {
  const [fotos, setFotos] = useState<FotoPortafolio[]>([])
  const [cargando, setCargando] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [intento, setIntento] = useState(0)

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

  async function subir(archivo: File, onProgress: (pct: number) => void) {
    const nueva = await subirFoto(archivo, onProgress)
    // Se agrega al inicio sin repetir la petición de la lista completa.
    setFotos((previas) => [aFoto(nueva), ...previas])
  }

  return (
    <GaleriaPortafolio
      fotos={fotos}
      cargando={cargando}
      error={error}
      onReintentar={reintentar}
      onUpload={subir}
    />
  )
}

export default PortafolioPage
