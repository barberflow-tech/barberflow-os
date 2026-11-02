import {
  CalendarAvailability,
  type DayAvailability,
} from '@/components/booking/CalendarAvailability'
import { useBookingStore } from '@/stores/useBookingStore'

const disponibilidadDePrueba: DayAvailability = {
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

// Vista solo de desarrollo: el calendario con datos de prueba que antes vivía en App.tsx.
export function DevCalendarioPage() {
  const { selectedTime } = useBookingStore()

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-slate-100 p-4 sm:p-8 dark:bg-gray-950">
      <CalendarAvailability availabilityData={disponibilidadDePrueba} />

      {selectedTime && (
        <div className="mt-6 rounded-2xl bg-blue-600 p-4 text-sm font-semibold text-white shadow-lg">
          Hora seleccionada en Zustand: <strong>{selectedTime}</strong>
        </div>
      )}
    </div>
  )
}

export default DevCalendarioPage
