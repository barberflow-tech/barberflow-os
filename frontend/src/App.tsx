import { Navigate, Route, Routes } from 'react-router-dom'
import { BarberosManager } from '@/components/admin/BarberosManager'
import { HorariosManager } from '@/components/admin/HorariosManager'
import { RolesManager } from '@/components/admin/RolesManager'
import { ServicesManager } from '@/components/admin/ServicesManager'
import { RoleGuard } from '@/components/auth/RoleGuard'
import { AvisoSesionCerrada } from '@/components/layout/AvisoSesionCerrada'
import { ThemeToggle } from '@/components/ui/ThemeToggle'
import AdminPage from '@/pages/AdminPage'
import BienvenidaPage from '@/pages/BienvenidaPage'
import DevCalendarioPage from '@/pages/DevCalendarioPage'
import InicioPage from '@/pages/InicioPage'
import LoginPage from '@/pages/LoginPage'
import NoAutorizadoPage from '@/pages/NoAutorizadoPage'
import { PerfilPage } from '@/pages/PerfilPage'
import PerfilAdminPage from '@/pages/PerfilAdminPage'
import PortafolioPage from '@/pages/PortafolioPage'
import ReservarPage from '@/pages/ReservarPage'

export function App() {
  return (
    <>
      <Routes>
        <Route path="/" element={<InicioPage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/registro" element={<LoginPage />} />
        <Route path="/restablecer" element={<LoginPage />} />
        <Route path="/reservar" element={<ReservarPage />} />
        <Route path="/no-autorizado" element={<NoAutorizadoPage />} />

        <Route element={<RoleGuard allowedRoles={['admin', 'barbero', 'cliente']} />}>
          <Route path="/bienvenida" element={<BienvenidaPage />} />
        </Route>

        <Route element={<RoleGuard allowedRoles={['cliente']} />}>
          <Route path="/perfil" element={<PerfilPage />} />
        </Route>

        <Route element={<RoleGuard allowedRoles={['barbero']} />}>
          <Route path="/barbero/portafolio" element={<PortafolioPage />} />
        </Route>

        {/* Rutas exclusivas de Administrador */}
        <Route element={<RoleGuard allowedRoles={['admin']} />}>
          <Route path="/admin" element={<AdminPage />} />
          <Route path="/admin/servicios" element={<ServicesManager />} />
          <Route path="/admin/barberos" element={<BarberosManager />} />
          <Route path="/admin/horarios" element={<HorariosManager />} />
          <Route path="/admin/usuarios" element={<RolesManager />} />
          <Route path="/admin/perfil" element={<PerfilAdminPage />} />
        </Route>

        {import.meta.env.DEV && (
          <Route path="/dev/calendario" element={<DevCalendarioPage />} />
        )}

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
      <AvisoSesionCerrada />
      <ThemeToggle />
    </>
  )
}

export default App
