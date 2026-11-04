import { CalendarPlus, Scissors, type LucideIcon } from 'lucide-react'
import { Link } from 'react-router-dom'
import { AdminShell } from '@/components/admin/AdminShell'

const secciones: { to: string; titulo: string; detalle: string; icono: LucideIcon }[] =
  [
    {
      to: '/admin/servicios',
      titulo: 'Catálogo de servicios',
      detalle: 'Define nombre, precio, duración y categoría de cada servicio.',
      icono: Scissors,
    },
    {
      to: '/reservar',
      titulo: 'Nuevo agendamiento',
      detalle: 'Reserva una cita para un cliente en pocos pasos.',
      icono: CalendarPlus,
    },
  ]

export function AdminPage() {
  return (
    <AdminShell>
      <p className="mb-4 flex items-center gap-3 text-xs font-semibold tracking-[0.22em] text-brand uppercase">
        <span className="h-px w-8 bg-brand" />
        Administración
      </p>
      <h1 className="font-['Playfair_Display',serif] text-4xl leading-tight sm:text-5xl">
        Panel de administración
      </h1>
      <p className="mt-3 max-w-xl text-app-fg/60">
        Gestiona lo que verán tus clientes: tus servicios y las reservas.
      </p>

      <ul className="mt-12 grid gap-5 sm:grid-cols-2">
        {secciones.map(({ to, titulo, detalle, icono: Icono }) => (
          <li key={to}>
            <Link
              to={to}
              className="group flex h-full flex-col gap-4 rounded-2xl border border-app-fg/10 bg-app-fg/[0.03] p-6 transition hover:border-brand/60 hover:bg-app-fg/[0.06]"
            >
              <span className="grid size-12 place-items-center rounded-full border border-brand/40 text-brand">
                <Icono className="size-5" aria-hidden="true" />
              </span>
              <span className="font-['Playfair_Display',serif] text-2xl">{titulo}</span>
              <span className="text-sm text-app-fg/55">{detalle}</span>
              <span className="mt-auto text-sm font-semibold text-brand transition group-hover:translate-x-1">
                Abrir →
              </span>
            </Link>
          </li>
        ))}
      </ul>
    </AdminShell>
  )
}

export default AdminPage
