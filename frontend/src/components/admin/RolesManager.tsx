import { Search } from 'lucide-react'
import { type FormEvent, useEffect, useState } from 'react'
import {
  cambiarRolApi,
  listarUsuariosApi,
  type UsuarioConRol,
  UsuariosError,
} from '@/lib/usuariosApi'
import { cn } from '@/lib/utils'
import { type Role, useAuthStore } from '@/stores/useAuthStore'
import { AdminShell } from './AdminShell'

const ROLES: { valor: Role; etiqueta: string }[] = [
  { valor: 'admin', etiqueta: 'Administrador' },
  { valor: 'barbero', etiqueta: 'Barbero' },
  { valor: 'cliente', etiqueta: 'Cliente' },
]
const etiquetaDe = (rol: Role) => ROLES.find((r) => r.valor === rol)?.etiqueta ?? rol

const campo =
  'w-full rounded-xl border border-app-fg/15 bg-app-fg/5 px-4 py-3 text-sm text-app-fg placeholder:text-app-fg/30 focus:border-brand focus:outline-none'
const botonDorado =
  'inline-flex items-center justify-center gap-2 rounded-full bg-brand px-5 py-2.5 text-sm font-semibold text-brand-fg transition hover:bg-brand-hover'
const botonLinea =
  'inline-flex items-center justify-center gap-2 rounded-full border border-app-fg/15 px-4 py-2 text-sm font-medium text-app-fg/80 transition hover:border-brand/60 hover:text-app-fg'

const mensajeDe = (error: unknown) =>
  error instanceof UsuariosError ? error.message : 'Ocurrió un error inesperado.'

/** Pantalla del admin para asignar roles (SCRUM-70 / HU-09). */
export function RolesManager() {
  const yo = useAuthStore((state) => state.user)
  const [usuarios, setUsuarios] = useState<UsuarioConRol[]>([])
  const [busqueda, setBusqueda] = useState<UsuarioConRol[] | null>(null)
  const [correo, setCorreo] = useState('')
  const [cargando, setCargando] = useState(true)
  const [guardando, setGuardando] = useState<number | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [aviso, setAviso] = useState<string | null>(null)

  useEffect(() => {
    let vigente = true
    listarUsuariosApi()
      .then((lista) => vigente && setUsuarios(lista))
      .catch((e: unknown) => vigente && setError(mensajeDe(e)))
      .finally(() => vigente && setCargando(false))
    return () => {
      vigente = false
    }
  }, [])

  async function buscar(evento: FormEvent) {
    evento.preventDefault()
    const email = correo.trim()
    if (!email) return
    setError(null)
    setAviso(null)
    try {
      setBusqueda(await listarUsuariosApi(email))
    } catch (e) {
      setError(mensajeDe(e))
    }
  }

  function verTodos() {
    setBusqueda(null)
    setCorreo('')
  }

  async function cambiarRol(usuario: UsuarioConRol, rol: Role) {
    if (rol === usuario.role) return
    setError(null)
    setAviso(null)
    setGuardando(usuario.id)
    try {
      const actualizado = await cambiarRolApi(usuario.id, rol)
      const reemplazar = (lista: UsuarioConRol[]) =>
        lista.map((u) => (u.id === actualizado.id ? actualizado : u))
      setBusqueda((lista) => (lista ? reemplazar(lista) : lista))
      setUsuarios((lista) =>
        // Un usuario recién vinculado a la barbería pasa a la lista principal.
        actualizado.en_barberia && !lista.some((u) => u.id === actualizado.id)
          ? [...lista, actualizado].sort((a, b) => a.email.localeCompare(b.email))
          : reemplazar(lista),
      )
      setAviso(`${actualizado.email} ahora es ${etiquetaDe(actualizado.role)}.`)
    } catch (e) {
      setError(mensajeDe(e))
    } finally {
      setGuardando(null)
    }
  }

  const visibles = busqueda ?? usuarios

  return (
    <AdminShell>
      <div className="mb-10">
        <p className="mb-4 flex items-center gap-3 text-xs font-semibold tracking-[0.22em] text-brand uppercase">
          <span className="h-px w-8 bg-brand" />
          Usuarios
        </p>
        <h1 className="font-['Playfair_Display',serif] text-4xl leading-tight sm:text-5xl">
          Usuarios y roles
        </h1>
        <p className="mt-3 max-w-xl text-app-fg/60">
          Define quién administra, quién atiende como barbero y quién es cliente. El
          cambio rige desde la siguiente acción del usuario.
        </p>
      </div>

      <form
        onSubmit={buscar}
        className="mb-8 flex flex-col gap-3 sm:flex-row sm:items-end"
      >
        <div className="flex-1">
          <label
            htmlFor="buscar-correo"
            className="mb-1.5 block text-xs font-semibold tracking-wide text-app-fg/60 uppercase"
          >
            Buscar por correo
          </label>
          <input
            id="buscar-correo"
            type="email"
            value={correo}
            onChange={(e) => setCorreo(e.target.value)}
            placeholder="cliente@correo.com"
            className={campo}
          />
        </div>
        <button type="submit" className={botonDorado}>
          <Search className="size-4" aria-hidden="true" />
          Buscar
        </button>
        {busqueda && (
          <button type="button" onClick={verTodos} className={botonLinea}>
            Ver todos
          </button>
        )}
      </form>
      <p className="-mt-5 mb-8 text-xs text-app-fg/45">
        Escribe el correo completo para encontrar a un cliente que aún no es de tu
        barbería. Al hacerlo barbero o administrador, queda vinculado a ella.
      </p>

      {error && (
        <p role="alert" className="mb-6 text-sm text-red-600 dark:text-red-400">
          {error}
        </p>
      )}
      {aviso && (
        <p role="status" className="mb-6 text-sm text-brand">
          {aviso}
        </p>
      )}
      {cargando && <p className="text-sm text-app-fg/50">Cargando usuarios…</p>}
      {!cargando && busqueda?.length === 0 && (
        <p className="text-sm text-app-fg/50">
          No hay ningún usuario con ese correo, o pertenece a otra barbería.
        </p>
      )}

      {visibles.length > 0 && (
        <div className="overflow-x-auto rounded-2xl border border-app-fg/10">
          <table className="w-full text-left text-sm">
            <thead className="bg-app-fg/[0.03] text-xs tracking-wide text-app-fg/50 uppercase">
              <tr>
                <th className="px-5 py-3 font-semibold">Usuario</th>
                <th className="px-5 py-3 font-semibold">Barbería</th>
                <th className="px-5 py-3 font-semibold">Rol</th>
              </tr>
            </thead>
            <tbody>
              {visibles.map((usuario) => {
                const esYo = usuario.id === yo?.id
                return (
                  <tr key={usuario.id} className="border-t border-app-fg/10">
                    <td className="px-5 py-4">
                      <span className="block font-medium text-app-fg">
                        {usuario.full_name || usuario.email}
                        {esYo && (
                          <span className="ml-2 rounded-full border border-brand/40 px-2 py-0.5 text-xs text-brand">
                            Tú
                          </span>
                        )}
                      </span>
                      {usuario.full_name && (
                        <span className="text-xs text-app-fg/50">{usuario.email}</span>
                      )}
                    </td>
                    <td
                      className={cn(
                        'px-5 py-4',
                        usuario.en_barberia ? 'text-app-fg/70' : 'text-app-fg/45',
                      )}
                    >
                      {usuario.en_barberia ? 'Tu barbería' : 'Sin barbería'}
                    </td>
                    <td className="px-5 py-4">
                      <select
                        aria-label={`Rol de ${usuario.email}`}
                        value={usuario.role}
                        disabled={esYo || guardando === usuario.id}
                        title={esYo ? 'No puedes cambiar tu propio rol.' : undefined}
                        onChange={(e) =>
                          void cambiarRol(usuario, e.target.value as Role)
                        }
                        className={cn(campo, 'py-2 disabled:opacity-50')}
                      >
                        {ROLES.map(({ valor, etiqueta }) => (
                          <option key={valor} value={valor}>
                            {etiqueta}
                          </option>
                        ))}
                      </select>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </AdminShell>
  )
}
