import { Link } from 'react-router-dom'

export function NoAutorizadoPage() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-4 bg-slate-100 p-6 text-center">
      <h1 className="text-2xl font-bold text-slate-900">No autorizado</h1>
      <p className="text-slate-600">Tu cuenta no tiene permiso para ver esta página.</p>
      <Link to="/" className="font-semibold text-blue-700 underline">
        Volver al inicio
      </Link>
    </main>
  )
}

export default NoAutorizadoPage
