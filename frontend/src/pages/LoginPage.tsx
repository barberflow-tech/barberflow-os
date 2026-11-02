import '@fontsource-variable/inter'
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

  return (
    <main className="flex min-h-screen items-center justify-center bg-[#F1F5F9] p-4 font-[Inter_Variable] sm:p-8">
      <LoginForm />
    </main>
  )
}

export default LoginPage
