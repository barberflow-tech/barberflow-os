import '@fontsource-variable/inter'
import '@fontsource/barlow-condensed/600.css'
import '@fontsource/barlow-condensed/700.css'
import { ArrowLeft, Scissors } from 'lucide-react'
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
    <div className="flex min-h-screen flex-col bg-[#FAFAF8] font-[Inter_Variable] text-[#101820] dark:bg-[#101820] dark:text-[#F7F1E8]">
      <Navbar />
      <main className="relative flex flex-1 justify-center overflow-hidden p-4 sm:p-8">
        <div
          className="bf-patron-rayas pointer-events-none absolute inset-0 opacity-40"
          aria-hidden="true"
        />
        <div className="relative w-full max-w-3xl">
          {!reservaConfirmada && (
            <Link
              to="/"
              className="mb-4 inline-flex items-center gap-1.5 text-sm font-medium text-[#101820]/60 transition-colors hover:text-[#B3263B] dark:text-[#F7F1E8]/60 dark:hover:text-[#E5283C]"
            >
              <ArrowLeft className="size-4" aria-hidden="true" />
              Volver al inicio
            </Link>
          )}
          <header className="mb-6 flex items-start gap-3">
            <span
              className="mt-1 grid size-10 shrink-0 place-items-center rounded-lg bg-[#101820] text-[#F7F1E8] dark:bg-[#F7F1E8] dark:text-[#101820]"
              aria-hidden="true"
            >
              <Scissors className="size-5" />
            </span>
            <div>
              <h1 className={`${titulo} text-3xl`}>Nuevo agendamiento</h1>
              <p className="text-sm text-[#101820]/60 dark:text-[#F7F1E8]/60">
                Crea una reserva en pocos pasos
              </p>
            </div>
          </header>
          <ReservaWizard />
        </div>
      </main>
      <Footer />
    </div>
  )
}

export default ReservarPage
