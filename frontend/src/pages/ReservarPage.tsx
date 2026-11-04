import '@fontsource-variable/inter'
import '@fontsource/barlow-condensed/600.css'
import '@fontsource/barlow-condensed/700.css'
import { ArrowLeft } from 'lucide-react'
import { Link } from 'react-router-dom'
import { ReservaWizard } from '@/components/booking/wizard/ReservaWizard'
import { titulo } from '@/components/booking/wizard/estilos'
import { Footer } from '@/components/layout/Footer'
import { Navbar } from '@/components/layout/Navbar'
import { useReservaWizardStore } from '@/stores/useReservaWizardStore'

export function ReservarPage() {
  // Al confirmar, la pantalla de éxito ya trae su propio «Volver al inicio».
  const reservaConfirmada = useReservaWizardStore((s) => !!s.cita)

  return (
    <div className="flex min-h-screen flex-col bg-[#F1F5F9] font-[Inter_Variable] dark:bg-[#0f1210]">
      <Navbar />
      <main className="flex flex-1 justify-center p-4 sm:p-8">
        <div className="w-full max-w-3xl">
          {!reservaConfirmada && (
            <Link
              to="/"
              className="mb-4 inline-flex items-center gap-1.5 text-sm font-medium text-slate-500 transition-colors hover:text-[#0B1B3A] dark:text-white/55 dark:hover:text-[#f4f1e9]"
            >
              <ArrowLeft className="size-4" aria-hidden="true" />
              Volver al inicio
            </Link>
          )}
          <header className="mb-6">
            <h1 className={`${titulo} text-3xl`}>Nuevo agendamiento</h1>
            <p className="text-sm text-slate-500 dark:text-white/55">
              Crea una reserva en pocos pasos
            </p>
          </header>
          <ReservaWizard />
        </div>
      </main>
      <Footer />
    </div>
  )
}

export default ReservarPage
