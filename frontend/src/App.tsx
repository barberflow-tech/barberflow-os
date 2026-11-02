import { useState } from 'react'
import { LoginForm } from './components/auth/LoginForm'
import {
  CalendarAvailability,
  type DayAvailability,
} from './components/booking/CalendarAvailability'

const mockAvailability: DayAvailability = {
  dateString: 'Domingo, 11 De Octubre',
  barberName: 'Thiago Angulo',
  configuredHours: 8,
  isWorkingDay: true,
  slots: [
    { id: '1', time: '09:00 AM', status: 'available', period: 'morning' },
    { id: '2', time: '09:30 AM', status: 'blocked', period: 'morning' },
    { id: '3', time: '10:00 AM', status: 'available', period: 'morning' },
    { id: '4', time: '02:00 PM', status: 'available', period: 'afternoon' },
    { id: '5', time: '02:30 PM', status: 'reserved', period: 'afternoon' },
    { id: '6', time: '03:00 PM', status: 'available', period: 'afternoon' },
  ],
}

export function App() {
  // Estado local para alternar entre páginas durante el desarrollo local
  const [currentView, setCurrentView] = useState<'login' | 'calendar'>('login')

  return (
    <div className="min-h-screen bg-slate-100 dark:bg-gray-950 p-4 sm:p-8 flex flex-col items-center justify-center">
      {/* Barra superior temporal para cambiar de vista */}
      <nav className="mb-8 flex gap-3 bg-white dark:bg-gray-900 p-2 rounded-2xl shadow-sm border border-slate-200 dark:border-gray-800">
        <button
          onClick={() => setCurrentView('login')}
          className={`px-4 py-2 rounded-xl text-xs font-bold transition-all ${
            currentView === 'login'
              ? 'bg-red-600 text-white shadow-md'
              : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-gray-800'
          }`}
        >
          Vista: Login (SUB-06-B)
        </button>
        <button
          onClick={() => setCurrentView('calendar')}
          className={`px-4 py-2 rounded-xl text-xs font-bold transition-all ${
            currentView === 'calendar'
              ? 'bg-red-600 text-white shadow-md'
              : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-gray-800'
          }`}
        >
          Vista: Calendario (HU-01)
        </button>
      </nav>

      {/* Renderizado Condicional: Pagina 1 o Pagina 2 */}
      {currentView === 'login' ? (
        <LoginForm />
      ) : (
        <CalendarAvailability availabilityData={mockAvailability} />
      )}
    </div>
  )
}

export default App
