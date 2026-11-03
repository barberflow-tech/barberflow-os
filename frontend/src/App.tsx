import { Navigate, Route, Routes } from 'react-router-dom'
import { ServicesManager } from '@/components/admin/ServicesManager'
import { RoleGuard } from '@/components/auth/RoleGuard'
import AdminPage from '@/pages/AdminPage'
import BienvenidaPage from '@/pages/BienvenidaPage'
import DevCalendarioPage from '@/pages/DevCalendarioPage'
import InicioPage from '@/pages/InicioPage'
import LoginPage from '@/pages/LoginPage'
import NoAutorizadoPage from '@/pages/NoAutorizadoPage'
import PortafolioPage from '@/pages/PortafolioPage'
import ReservarPage from '@/pages/ReservarPage'

export function App() {
  return (
    <Routes>
      <Route path="/" element={<InicioPage />} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/reservar" element={<ReservarPage />} />
      <Route path="/no-autorizado" element={<NoAutorizadoPage />} />

      <Route element={<RoleGuard allowedRoles={['admin', 'barbero', 'cliente']} />}>
        <Route path="/bienvenida" element={<BienvenidaPage />} />
      </Route>

      <Route element={<RoleGuard allowedRoles={['admin']} />}>
        <Route path="/admin" element={<AdminPage />} />
        <Route path="/admin/portafolio" element={<PortafolioPage />} />
        <Route
          path="/admin/servicios"
          element={
            <div className="flex min-h-screen items-center justify-center bg-slate-100 p-6 dark:bg-gray-950">
              <ServicesManager />
            </div>
          }
        />
      </Route>

      {import.meta.env.DEV && (
        <Route path="/dev/calendario" element={<DevCalendarioPage />} />
      )}

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

export default App
