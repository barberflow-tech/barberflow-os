import { Link } from 'react-router-dom'
import { useAuthStore } from '@/stores/useAuthStore'

export function AdminPage() {
  const user = useAuthStore((state) => state.user)
  const clearSession = useAuthStore((state) => state.clearSession)

  return (
    <main className="mx-auto flex min-h-screen max-w-3xl flex-col gap-6 bg-slate-100 p-6 sm:p-10">
      <header>
        <h1 className="text-2xl font-bold text-slate-900">Panel de administración</h1>
        <p className="text-sm text-slate-600">Sesión: {user?.email}</p>
      </header>
      <nav aria-label="Secciones del panel" className="grid gap-3 sm:grid-cols-2">
        <Link
          to="/admin/portafolio"
          className="rounded-2xl bg-white p-5 font-semibold text-slate-900 shadow-sm hover:shadow-md"
        >
          Portafolio
        </Link>
        <Link
          to="/reservar"
          className="rounded-2xl bg-white p-5 font-semibold text-slate-900 shadow-sm hover:shadow-md"
        >
          Nuevo agendamiento
        </Link>
      </nav>
      <button
        type="button"
        onClick={clearSession}
        className="self-start font-semibold text-slate-700 underline"
      >
        Cerrar sesión
      </button>
    </main>
  )
}

export default AdminPage
