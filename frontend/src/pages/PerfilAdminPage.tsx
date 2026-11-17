import { Mail, Scissors, ShieldCheck, UserRound } from 'lucide-react'
import { AdminShell } from '@/components/admin/AdminShell'
import { useAuthStore, type Role } from '@/stores/useAuthStore'

const ROL: Record<Role, string> = {
  admin: 'Administrador',
  barbero: 'Barbero',
  cliente: 'Cliente',
}

function Dato({
  icono: Icono,
  etiqueta,
  valor,
}: {
  icono: typeof Mail
  etiqueta: string
  valor: string
}) {
  return (
    <li className="flex items-center gap-4 rounded-2xl border border-app-fg/10 bg-app-fg/[0.03] p-5">
      <span className="grid size-11 shrink-0 place-items-center rounded-full border border-brand/40 text-brand">
        <Icono className="size-5" aria-hidden="true" />
      </span>
      <span className="min-w-0">
        <span className="block text-xs font-semibold tracking-[0.18em] text-app-fg/45 uppercase">
          {etiqueta}
        </span>
        <span className="block truncate text-base text-app-fg">{valor}</span>
      </span>
    </li>
  )
}

/** Datos de la cuenta con la que el administrador inició sesión. */
export function PerfilAdminPage() {
  const user = useAuthStore((s) => s.user)
  const nombre = user?.fullName?.trim() || ''
  const inicial = (nombre || user?.email || '?').charAt(0).toUpperCase()

  return (
    <AdminShell>
      <div className="grid items-center gap-12 lg:grid-cols-[1fr_minmax(0,26rem)]">
        <div>
          <p className="mb-4 flex items-center gap-3 text-xs font-semibold tracking-[0.22em] text-brand uppercase">
            <span className="h-px w-8 bg-brand" />
            Cuenta
          </p>
          <h1 className="font-['Playfair_Display',serif] text-4xl leading-tight sm:text-5xl">
            Mi perfil
          </h1>

          <div className="mt-10 flex items-center gap-5">
            <span
              aria-hidden="true"
              className="grid size-20 shrink-0 place-items-center rounded-full bg-brand font-['Playfair_Display',serif] text-3xl text-brand-fg"
            >
              {inicial}
            </span>
            <div className="min-w-0">
              <p className="truncate font-['Playfair_Display',serif] text-2xl">
                {nombre || 'Sin nombre registrado'}
              </p>
              <p className="truncate text-app-fg/55">{user?.email}</p>
            </div>
          </div>

          <ul className="mt-10 grid max-w-xl gap-4 sm:grid-cols-2">
            <Dato
              icono={UserRound}
              etiqueta="Nombre"
              valor={nombre || 'Sin nombre registrado'}
            />
            <Dato icono={Mail} etiqueta="Correo" valor={user?.email ?? '—'} />
            <Dato
              icono={ShieldCheck}
              etiqueta="Rol"
              valor={user ? ROL[user.role] : '—'}
            />
          </ul>
        </div>

        <div
          data-testid="perfil-decoracion"
          aria-hidden="true"
          className="relative hidden aspect-[4/5] overflow-hidden rounded-3xl bg-[#101820] p-8 text-[#F7F1E8] shadow-[0_30px_60px_-30px_rgb(16_24_32_/_60%)] lg:flex lg:flex-col lg:justify-between"
        >
          <div className="bf-patron-rayas pointer-events-none absolute inset-0 opacity-70" />
          <div className="relative flex items-center gap-3">
            <span className="grid size-11 place-items-center rounded-full border border-[#E5283C]/60 text-[#E5283C]">
              <Scissors className="size-5" />
            </span>
            <span className="text-sm font-semibold tracking-[0.2em]">BARBERFLOW</span>
          </div>
          <div className="relative flex flex-col items-center gap-5">
            <div className="h-44 w-14 rounded-full border-4 border-[#F7F1E8]/80 bg-[repeating-linear-gradient(-45deg,#B3263B_0_14px,#F7F1E8_14px_28px,#174A7E_28px_42px,#F7F1E8_42px_56px)]" />
            <span className="rounded-full border border-[#F7F1E8]/25 px-4 py-1.5 text-xs tracking-[0.22em] uppercase">
              {user ? ROL[user.role] : ''}
            </span>
          </div>
          <p className="relative font-['Playfair_Display',serif] text-xl leading-snug italic text-[#F7F1E8]/80">
            Tu barbería, bajo control.
          </p>
        </div>
      </div>
    </AdminShell>
  )
}

export default PerfilAdminPage
