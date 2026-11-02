import { GaleriaPortafolio } from '@/components/portfolio/GaleriaPortafolio'

// La subida real a Supabase Storage pertenece a SCRUM-35; mientras tanto se simula.
async function subirSimulada(_archivo: File, onProgress: (pct: number) => void) {
  for (const pct of [25, 60, 100]) {
    await new Promise((resolve) => setTimeout(resolve, 150))
    onProgress(pct)
  }
}

export function PortafolioPage() {
  return <GaleriaPortafolio onUpload={subirSimulada} />
}

export default PortafolioPage
