import '@fontsource-variable/inter'
import '@fontsource/barlow-condensed/600.css'
import '@fontsource/barlow-condensed/700.css'
import { ReservaWizard } from '@/components/booking/wizard/ReservaWizard'
import { titulo } from '@/components/booking/wizard/estilos'

export function ReservarPage() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-[#F1F5F9] p-4 font-[Inter_Variable] sm:p-8">
      <div className="w-full max-w-3xl">
        <header className="mb-6">
          <h1 className={`${titulo} text-3xl`}>Nuevo agendamiento</h1>
          <p className="text-sm text-slate-500">Crea una reserva en pocos pasos</p>
        </header>
        <ReservaWizard />
      </div>
    </main>
  )
}

export default ReservarPage
