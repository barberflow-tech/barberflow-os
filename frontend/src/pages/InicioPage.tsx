import { Link } from 'react-router-dom'

// Portada provisional: la landing con diseño real depende del mockup de Figma.
export function InicioPage() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-8 bg-[#0f1210] p-6 text-center text-[#f4f1e9]">
      <div>
        <h1 className="text-4xl font-bold tracking-tight sm:text-5xl">BarberFlow</h1>
        <p className="mt-3 text-base text-[#f4f1e9]/70">
          Agenda tu cita en la barbería en pocos pasos
        </p>
      </div>
      <nav
        aria-label="Acciones principales"
        className="flex flex-col gap-3 sm:flex-row"
      >
        <Link
          to="/reservar"
          className="rounded-full bg-[#d7b36a] px-8 py-3 font-semibold text-[#0f1210] transition hover:bg-[#e3c27d]"
        >
          Reservar cita
        </Link>
        <Link
          to="/login"
          className="rounded-full border border-[#d7b36a]/60 px-8 py-3 font-semibold text-[#d7b36a] transition hover:bg-[#d7b36a]/10"
        >
          Ingresar
        </Link>
      </nav>
    </main>
  )
}

export default InicioPage
