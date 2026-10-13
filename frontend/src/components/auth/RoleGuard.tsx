import { Navigate, Outlet } from 'react-router-dom'
import { useAuthStore, type Role } from '@/stores/useAuthStore'

interface RoleGuardProps {
  allowedRoles: Role[]
}

export function RoleGuard({ allowedRoles }: RoleGuardProps) {
  const user = useAuthStore((state) => state.user)
  const isHydrating = useAuthStore((state) => state.isHydrating)

  if (isHydrating) {
    return (
      <div role="status" aria-live="polite" className="p-6 text-center">
        Cargando sesión...
      </div>
    )
  }

  if (!user) {
    return <Navigate to="/login" replace />
  }

  if (!allowedRoles.includes(user.role)) {
    return <Navigate to="/no-autorizado" replace />
  }

  return <Outlet />
}
