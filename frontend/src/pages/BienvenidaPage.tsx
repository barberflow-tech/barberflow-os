import { Link } from 'react-router-dom'
import { useAuthStore } from '@/stores/useAuthStore'

// Pantalla genérica para roles cuya vista propia aún no existe (p. ej. barbero).
export function BienvenidaPage() {
  const user = useAuthStore((state) => state.user)
  const clearSession = useAuthStore((state) => state.clearSession)

  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-4 bg-slate-100 p-6 text-center">
      <h1 className="text-2xl font-bold text-slate-900">Bienvenido a BarberFlow</h1>
      <p className="text-slate-600">
        Sesión iniciada como <strong>{user?.email}</strong>. Tu panel estará disponible
        pronto.
      </p>
      <div className="flex gap-4">
        <Link to="/reservar" className="font-semibold text-blue-700 underline">
          Agendar una cita
        </Link>
        <button
          type="button"
          onClick={clearSession}
          className="font-semibold text-slate-700 underline"
        >
          Cerrar sesión
        </button>
      </div>
    </main>
  )
}

export default BienvenidaPage
