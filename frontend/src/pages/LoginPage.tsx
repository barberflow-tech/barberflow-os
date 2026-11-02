import { Navigate } from 'react-router-dom'
import { LoginForm } from '@/components/auth/LoginForm'
import { rutaPorRol } from '@/lib/rutas'
import { useAuthStore } from '@/stores/useAuthStore'

export function LoginPage() {
  const user = useAuthStore((state) => state.user)

  // Con la sesión ya iniciada (o restaurada por la cookie) no se vuelve a mostrar el login.
  if (user) {
    return <Navigate to={rutaPorRol(user.role)} replace />
  }

  return <LoginForm />
}

export default LoginPage
