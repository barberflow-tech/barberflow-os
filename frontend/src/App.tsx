import {
  CalendarAvailability,
  type DayAvailability,
} from './components/booking/CalendarAvailability'
import { useBookingStore } from './stores/useBookingStore'

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
  const { selectedTime } = useBookingStore()

  return (
    <div className="min-h-screen bg-slate-100 dark:bg-gray-950 p-4 sm:p-8 flex flex-col items-center justify-center">
      <CalendarAvailability availabilityData={mockAvailability} />

      {selectedTime && (
        <div className="mt-6 p-4 bg-blue-600 text-white rounded-2xl shadow-lg text-sm font-semibold">
          Hora seleccionada en Zustand: <strong>{selectedTime}</strong>
        </div>
      )}
    </div>
  )
}

export default App
