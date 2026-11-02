import { beforeEach, describe, expect, it } from 'vitest'
import type { Barbero, CitaConfirmada, Servicio } from '@/lib/reservaApi'
import { useReservaWizardStore } from './useReservaWizardStore'

const servicio: Servicio = {
  id: 1,
  nombre: 'Corte clásico',
  precio: 25000,
  duracionMin: 45,
}
const barbero: Barbero = {
  id: 1,
  nombre: 'Thiago',
  rol: 'Master barber',
  calificacion: 4.9,
}
const cita: CitaConfirmada = {
  id: 10,
  estado: 'PENDING',
  servicio,
  barbero,
  inicio: '2026-11-04T11:30:00-05:00',
  total: 25000,
}

describe('useReservaWizardStore', () => {
  beforeEach(() => useReservaWizardStore.getState().reiniciar())

  it('empieza en el paso 1 sin selecciones', () => {
    const s = useReservaWizardStore.getState()

    expect(s.paso).toBe(1)
    expect(s.servicio).toBeNull()
    expect(s.barbero).toBeNull()
    expect(s.fecha).toBeNull()
    expect(s.hora).toBeNull()
    expect(s.cita).toBeNull()
  })

  it('no avanza de paso hasta completar la selección del paso actual', () => {
    const s = useReservaWizardStore.getState()

    // Dado el paso 1 sin servicio, Cuando intenta avanzar, Entonces se queda en el paso 1
    s.siguiente()
    expect(useReservaWizardStore.getState().paso).toBe(1)

    // Dado un servicio elegido, Cuando avanza, Entonces pasa al paso 2
    s.seleccionarServicio(servicio)
    s.siguiente()
    expect(useReservaWizardStore.getState().paso).toBe(2)
  })

  it('avanza y retrocede conservando las selecciones', () => {
    const s = useReservaWizardStore.getState()
    s.seleccionarServicio(servicio)
    s.siguiente()
    s.seleccionarBarbero(barbero)
    s.siguiente()
    s.seleccionarFecha('2026-11-04')
    s.seleccionarHora('11:30')
    s.siguiente()
    expect(useReservaWizardStore.getState().paso).toBe(4)

    useReservaWizardStore.getState().atras()

    const despues = useReservaWizardStore.getState()
    expect(despues.paso).toBe(3)
    expect(despues.hora).toBe('11:30')
    expect(despues.servicio).toEqual(servicio)
  })

  it('al cambiar de fecha descarta la hora elegida', () => {
    const s = useReservaWizardStore.getState()
    s.seleccionarFecha('2026-11-04')
    s.seleccionarHora('11:30')

    s.seleccionarFecha('2026-11-05')

    expect(useReservaWizardStore.getState().hora).toBeNull()
  })

  it('al cambiar de barbero descarta la fecha y la hora', () => {
    const s = useReservaWizardStore.getState()
    s.seleccionarBarbero(barbero)
    s.seleccionarFecha('2026-11-04')
    s.seleccionarHora('11:30')

    s.seleccionarBarbero({ id: 2, nombre: 'Mateo', rol: 'Barber', calificacion: 4.7 })

    const despues = useReservaWizardStore.getState()
    expect(despues.fecha).toBeNull()
    expect(despues.hora).toBeNull()
  })

  it('al registrar la cita limpia las selecciones y conserva solo el resumen', () => {
    const s = useReservaWizardStore.getState()
    s.seleccionarServicio(servicio)
    s.seleccionarBarbero(barbero)
    s.seleccionarFecha('2026-11-04')
    s.seleccionarHora('11:30')

    s.registrarCita(cita)

    const despues = useReservaWizardStore.getState()
    expect(despues.cita).toEqual(cita)
    expect(despues.servicio).toBeNull()
    expect(despues.barbero).toBeNull()
    expect(despues.fecha).toBeNull()
    expect(despues.hora).toBeNull()
    expect(despues.paso).toBe(1)
  })

  it('reiniciar deja el wizard en su estado inicial', () => {
    const s = useReservaWizardStore.getState()
    s.seleccionarServicio(servicio)
    s.registrarCita(cita)

    s.reiniciar()

    const despues = useReservaWizardStore.getState()
    expect(despues.cita).toBeNull()
    expect(despues.servicio).toBeNull()
    expect(despues.paso).toBe(1)
  })
})
