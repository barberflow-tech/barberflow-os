import { create } from 'zustand'

interface BookingState {
  selectedDate: string | null
  selectedSlotId: string | null
  selectedTime: string | null
  setSelectedDate: (date: string) => void
  setSelectedSlot: (slotId: string, time: string) => void
  resetBooking: () => void
}

export const useBookingStore = create<BookingState>((set) => ({
  selectedDate: null,
  selectedSlotId: null,
  selectedTime: null,
  setSelectedDate: (date) => set({ selectedDate: date }),
  setSelectedSlot: (slotId, time) =>
    set({ selectedSlotId: slotId, selectedTime: time }),
  resetBooking: () =>
    set({ selectedDate: null, selectedSlotId: null, selectedTime: null }),
}))
