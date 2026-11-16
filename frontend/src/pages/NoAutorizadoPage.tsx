import { useNavigate } from 'react-router-dom'
import { ShieldAlert, ArrowLeft } from 'lucide-react'

export default function NoAutorizadoPage() {
  const navigate = useNavigate()

  return (
    <main className="flex min-h-screen flex-col items-center justify-center bg-slate-50 px-4 text-center dark:bg-slate-950">
      <div className="relative isolate overflow-hidden rounded-[32px] border border-slate-200 bg-white p-8 shadow-2xl shadow-slate-200/50 sm:max-w-md sm:p-12 dark:border-slate-800 dark:bg-slate-900 dark:shadow-black/50">
        {/* Efectos de iluminación de fondo */}
        <div className="absolute -left-12 -top-12 -z-10 h-40 w-40 rounded-full bg-red-500/10 blur-3xl dark:bg-red-500/20" />
        <div className="absolute -bottom-12 -right-12 -z-10 h-40 w-40 rounded-full bg-amber-500/10 blur-3xl dark:bg-amber-500/20" />

        <div className="mx-auto flex h-20 w-20 items-center justify-center rounded-3xl bg-red-50 text-red-500 dark:bg-red-500/10 dark:text-red-400">
          <ShieldAlert className="h-10 w-10" />
        </div>

        <h1 className="mt-6 text-4xl font-black tracking-tight text-slate-900 sm:text-5xl dark:text-white">
          403
        </h1>
        <h2 className="mt-2 text-lg font-extrabold text-slate-700 dark:text-slate-200">
          No autorizado
        </h2>

        <p className="mx-auto mt-4 max-w-[280px] text-sm leading-relaxed text-slate-500 dark:text-slate-400">
          Tu rol actual no cuenta con los permisos necesarios para visualizar el
          contenido de esta sección.
        </p>

        <button
          type="button"
          onClick={() => navigate('/')}
          className="mt-8 inline-flex w-full items-center justify-center gap-2 rounded-2xl bg-amber-400 px-6 py-3.5 text-sm font-black text-slate-950 shadow-lg shadow-amber-400/20 transition-all hover:-translate-y-0.5 hover:bg-amber-300 hover:shadow-amber-400/30 focus:outline-none focus:ring-4 focus:ring-amber-300/30"
        >
          <ArrowLeft className="h-4 w-4" />
          Volver al inicio
        </button>
      </div>
    </main>
  )
}
