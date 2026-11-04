import '@fontsource-variable/inter'
import '@fontsource/barlow-condensed/600.css'
import '@fontsource/barlow-condensed/700.css'
import { Navigate, useLocation, useNavigate } from 'react-router-dom'
import { LoginForm } from '@/components/auth/LoginForm'
import { Footer } from '@/components/layout/Footer'
import { Navbar } from '@/components/layout/Navbar'
import { rutaPorRol } from '@/lib/rutas'
import { useAuthStore } from '@/stores/useAuthStore'

/** Ingreso y registro comparten pantalla: /login y /registro abren cada pestaña. */
export function LoginPage() {
  const user = useAuthStore((state) => state.user)
  const { pathname } = useLocation()
  const navigate = useNavigate()

  // Con la sesión ya iniciada (o restaurada por la cookie) no se vuelve a mostrar el login.
  if (user) {
    return <Navigate to={rutaPorRol(user.role)} replace />
  }

  return (
    <div className="flex min-h-screen flex-col bg-[#F1F5F9] font-[Inter_Variable] text-[#0B1B3A] dark:bg-[#0f1210] dark:text-[#f4f1e9]">
      <Navbar />
      <main className="flex flex-1 items-center justify-center p-4 sm:p-8">
        <LoginForm
          pasoInicial={pathname === '/registro' ? 'register' : 'login'}
          onPasoChange={(paso) =>
            navigate(paso === 'register' ? '/registro' : '/login', { replace: true })
          }
        />
      </main>
      <Footer />
    </div>
  )
}

export default LoginPage
