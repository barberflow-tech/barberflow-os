import React, { useState } from 'react'
import { useBookingStore } from '../../stores/useBookingStore'

export interface TimeSlot {
  id: string
  time: string
  status: 'available' | 'reserved' | 'blocked'
  period: 'morning' | 'afternoon'
}

export interface DayAvailability {
  dateString: string
  barberName: string
  configuredHours: number
  isWorkingDay: boolean
  slots: TimeSlot[]
}

interface CalendarAvailabilityProps {
  availabilityData: DayAvailability
}

export const CalendarAvailability: React.FC<CalendarAvailabilityProps> = ({
  availabilityData,
}) => {
  const { selectedSlotId, setSelectedSlot } = useBookingStore()

  const [currentMonthDate, setCurrentMonthDate] = useState(new Date(2026, 9, 1))
  const [selectedDay, setSelectedDay] = useState<number>(11)
  const [localSlots, setLocalSlots] = useState<TimeSlot[]>(availabilityData.slots)

  const monthNames = [
    'ENERO',
    'FEBRERO',
    'MARZO',
    'ABRIL',
    'MAYO',
    'JUNIO',
    'JULIO',
    'AGOSTO',
    'SEPTIEMBRE',
    'OCTUBRE',
    'NOVIEMBRE',
    'DICIEMBRE',
  ]

  const handlePrevMonth = () => {
    setCurrentMonthDate((prev) => new Date(prev.getFullYear(), prev.getMonth() - 1, 1))
  }

  const handleNextMonth = () => {
    setCurrentMonthDate((prev) => new Date(prev.getFullYear(), prev.getMonth() + 1, 1))
  }

  const handleSelectDay = (day: number) => {
    setSelectedDay(day)
  }

  const handleBlockAction = () => {
    if (!selectedSlotId) {
      alert('Selecciona una franja horaria primero para cambiar su estado a Bloqueada.')
      return
    }
    setLocalSlots((prevSlots) =>
      prevSlots.map((slot) =>
        slot.id === selectedSlotId
          ? { ...slot, status: slot.status === 'blocked' ? 'available' : 'blocked' }
          : slot,
      ),
    )
  }

  const handleNotificationClick = () => {
    alert('Notificaciones: No hay alertas pendientes para este horario.')
  }

  const morningSlots = localSlots.filter((s) => s.period === 'morning')
  const afternoonSlots = localSlots.filter((s) => s.period === 'afternoon')

  const activeSlot = localSlots.find((s) => s.id === selectedSlotId)

  const daysInMonth = new Date(
    currentMonthDate.getFullYear(),
    currentMonthDate.getMonth() + 1,
    0,
  ).getDate()
  const calendarDays = Array.from({ length: daysInMonth }, (_, i) => i + 1)

  return (
    <div className="w-full max-w-5xl mx-auto space-y-6 p-4 sm:p-6 bg-slate-50/50 dark:bg-gray-950 rounded-3xl">
      {/* Encabezado Superior */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-2xl font-black text-slate-900 dark:text-white uppercase tracking-tight">
            Calendario y Disponibilidad
          </h1>
          <p className="text-sm text-slate-500 dark:text-slate-400">
            Configura tus franjas y controla la agenda del equipo
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={handleBlockAction}
            className="flex items-center gap-2 bg-red-600 hover:bg-red-700 active:scale-95 text-white font-semibold text-sm px-4 py-2.5 rounded-2xl shadow-sm transition-all cursor-pointer"
          >
            <span>+</span> Bloquear / Desbloquear horario
          </button>
          <button
            onClick={handleNotificationClick}
            className="p-2.5 bg-white dark:bg-gray-800 border border-slate-200 dark:border-gray-700 rounded-2xl text-slate-600 dark:text-slate-300 hover:bg-slate-100 cursor-pointer transition-all"
            title="Notificaciones"
          >
            🔔
          </button>
        </div>
      </div>

      {/* Grid de 2 Columnas */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* COLUMNA IZQUIERDA: Mini-Calendario */}
        <div className="lg:col-span-5 bg-white dark:bg-gray-900 p-6 rounded-3xl border border-slate-100 dark:border-gray-800 shadow-sm">
          <div className="flex justify-between items-center mb-6">
            <button
              onClick={handlePrevMonth}
              className="w-9 h-9 flex items-center justify-center border border-slate-200 dark:border-gray-700 rounded-xl text-slate-600 dark:text-slate-300 hover:bg-slate-100 cursor-pointer transition-all"
            >
              ‹
            </button>
            <div className="text-center">
              <h2 className="text-sm font-black text-slate-800 dark:text-white uppercase tracking-wider">
                {monthNames[currentMonthDate.getMonth()]}{' '}
                {currentMonthDate.getFullYear()}
              </h2>
              <p className="text-xs text-slate-400">Selecciona una fecha</p>
            </div>
            <button
              onClick={handleNextMonth}
              className="w-9 h-9 flex items-center justify-center border border-slate-200 dark:border-gray-700 rounded-xl text-slate-600 dark:text-slate-300 hover:bg-slate-100 cursor-pointer transition-all"
            >
              ›
            </button>
          </div>

          <div className="grid grid-cols-7 text-center text-xs font-bold text-slate-400 mb-3 uppercase">
            <span>LUN</span>
            <span>MAR</span>
            <span>MIÉ</span>
            <span>JUE</span>
            <span>VIE</span>
            <span>SÁB</span>
            <span>DOM</span>
          </div>

          <div className="grid grid-cols-7 gap-y-2 text-center text-sm">
            {calendarDays.map((day) => {
              const isSelected = day === selectedDay
              return (
                <div
                  key={day}
                  className="flex flex-col items-center justify-center h-10"
                >
                  <button
                    onClick={() => handleSelectDay(day)}
                    className={`w-9 h-9 rounded-2xl flex items-center justify-center font-semibold text-sm transition-all cursor-pointer ${
                      isSelected
                        ? 'bg-red-600 text-white font-bold shadow-md shadow-red-500/30'
                        : 'text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-gray-800'
                    }`}
                  >
                    {day}
                  </button>
                </div>
              )
            })}
          </div>

          <div className="flex items-center justify-between text-xs font-medium text-slate-500 dark:text-slate-400 mt-6 pt-4 border-t border-slate-100 dark:border-gray-800">
            <span className="flex items-center gap-1.5">
              <span className="w-2 h-2 bg-emerald-500 rounded-full"></span> Con citas
            </span>
            <span className="flex items-center gap-1.5">
              <span className="w-2 h-2 bg-slate-300 rounded-full"></span> No disponible
            </span>
            <span className="flex items-center gap-1.5">
              <span className="w-2 h-2 bg-red-600 rounded-full"></span> Seleccionado
            </span>
          </div>
        </div>

        {/* COLUMNA DERECHA: Horarios */}
        <div className="lg:col-span-7 bg-white dark:bg-gray-900 p-6 rounded-3xl border border-slate-100 dark:border-gray-800 shadow-sm space-y-6">
          <div className="flex justify-between items-start pb-4 border-b border-slate-100 dark:border-gray-800">
            <div>
              <h2 className="text-xl font-bold text-slate-900 dark:text-white">
                Día {selectedDay} de {monthNames[currentMonthDate.getMonth()]}
              </h2>
              <p className="text-sm text-slate-500 dark:text-slate-400">
                {availabilityData.barberName} · {availabilityData.configuredHours} horas
                configuradas
              </p>
            </div>
            <span className="bg-emerald-50 text-emerald-600 dark:bg-emerald-950/40 dark:text-emerald-400 text-xs font-bold px-3 py-1.5 rounded-full tracking-wider uppercase">
              DISPONIBLE
            </span>
          </div>

          {/* Mañana */}
          {morningSlots.length > 0 && (
            <div className="space-y-3">
              <span className="text-xs font-bold text-slate-400 uppercase tracking-wider block">
                ☀️ MAÑANA
              </span>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                {morningSlots.map((slot) => (
                  <button
                    key={slot.id}
                    onClick={() => setSelectedSlot(slot.id, slot.time)}
                    className={`p-3.5 rounded-2xl border text-left transition-all cursor-pointer flex flex-col justify-between ${
                      selectedSlotId === slot.id
                        ? 'border-red-600 ring-2 ring-red-600/20 bg-red-50/20 dark:bg-red-950/20'
                        : slot.status === 'available'
                          ? 'border-slate-200 dark:border-gray-700 bg-white dark:bg-gray-800 hover:border-slate-400'
                          : slot.status === 'reserved'
                            ? 'border-blue-100 bg-blue-50/50 dark:bg-blue-950/20 dark:border-blue-900/40'
                            : 'border-slate-100 bg-slate-50 dark:bg-gray-800/40 opacity-70'
                    }`}
                  >
                    <span
                      className={`text-base font-bold ${
                        slot.status === 'blocked'
                          ? 'text-slate-400 line-through'
                          : slot.status === 'reserved'
                            ? 'text-blue-600 dark:text-blue-400'
                            : selectedSlotId === slot.id
                              ? 'text-red-600 dark:text-red-400'
                              : 'text-slate-800 dark:text-white'
                      }`}
                    >
                      {slot.time}
                    </span>
                    <span
                      className={`text-xs font-semibold mt-1 capitalize ${
                        slot.status === 'available'
                          ? 'text-emerald-500'
                          : slot.status === 'reserved'
                            ? 'text-blue-500'
                            : 'text-slate-400'
                      }`}
                    >
                      {slot.status === 'available'
                        ? 'Disponible'
                        : slot.status === 'reserved'
                          ? 'Reservada'
                          : 'Bloqueada'}
                    </span>
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Tarde */}
          {afternoonSlots.length > 0 && (
            <div className="space-y-3">
              <span className="text-xs font-bold text-slate-400 uppercase tracking-wider block">
                📅 TARDE
              </span>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                {afternoonSlots.map((slot) => (
                  <button
                    key={slot.id}
                    onClick={() => setSelectedSlot(slot.id, slot.time)}
                    className={`p-3.5 rounded-2xl border text-left transition-all cursor-pointer flex flex-col justify-between ${
                      selectedSlotId === slot.id
                        ? 'border-red-600 ring-2 ring-red-600/20 bg-red-50/20 dark:bg-red-950/20'
                        : slot.status === 'available'
                          ? 'border-slate-200 dark:border-gray-700 bg-white dark:bg-gray-800 hover:border-slate-400'
                          : slot.status === 'reserved'
                            ? 'border-blue-100 bg-blue-50/50 dark:bg-blue-950/20 dark:border-blue-900/40'
                            : 'border-slate-100 bg-slate-50 dark:bg-gray-800/40 opacity-70'
                    }`}
                  >
                    <span
                      className={`text-base font-bold ${
                        slot.status === 'blocked'
                          ? 'text-slate-400 line-through'
                          : slot.status === 'reserved'
                            ? 'text-blue-600 dark:text-blue-400'
                            : selectedSlotId === slot.id
                              ? 'text-red-600 dark:text-red-400'
                              : 'text-slate-800 dark:text-white'
                      }`}
                    >
                      {slot.time}
                    </span>
                    <span
                      className={`text-xs font-semibold mt-1 capitalize ${
                        slot.status === 'available'
                          ? 'text-emerald-500'
                          : slot.status === 'reserved'
                            ? 'text-blue-500'
                            : 'text-slate-400'
                      }`}
                    >
                      {slot.status === 'available'
                        ? 'Disponible'
                        : slot.status === 'reserved'
                          ? 'Reservada'
                          : 'Bloqueada'}
                    </span>
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Banner si el horario está bloqueado */}
          {activeSlot?.status === 'blocked' && (
            <div className="p-4 bg-amber-50/80 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-800/50 rounded-2xl flex items-start gap-3">
              <span className="text-amber-600 dark:text-amber-400 text-lg">🔒</span>
              <p className="text-xs sm:text-sm text-amber-900 dark:text-amber-200 leading-relaxed">
                <strong>{activeSlot.time} está bloqueada.</strong> Este espacio se marcó
                como descanso. Puedes cambiar su estado con el botón superior.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
