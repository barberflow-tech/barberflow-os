import { describe, expect, it } from 'vitest'
import type { CitaConfirmada } from '@/lib/reservaApi'
import { cancelacionSeraTardia, puedeReprogramar, textoHoras } from './reglas'

const HORA = 60 * 60 * 1000
const AHORA = Date.parse('2026-11-20T12:00:00-05:00')

const cita = (reprogramarAntes?: string): CitaConfirmada => ({
  id: 1,
  estado: 'PENDING',
  servicio: { id: 2, nombre: 'Corte', precio: 35000, duracionMin: 40 },
  barbero: { id: 9, nombre: 'Thiago', rol: 'Barbero', calificacion: 0 },
  inicio: '2026-11-20T15:00:00-05:00',
  total: 35000,
  reprogramarAntes,
  horasAntelacion: 2,
})

const limite = (deltaHoras: number) => new Date(AHORA + deltaHoras * HORA).toISOString()

describe('reglas de antelación del perfil', () => {
  it('Dada una hora límite futura, Cuando se consulta, Entonces aún se puede reprogramar', () => {
    expect(puedeReprogramar(cita(limite(1)), AHORA)).toBe(true)
    expect(cancelacionSeraTardia(cita(limite(1)), AHORA)).toBe(false)
  })

  it('Dada una hora límite ya pasada, Cuando se consulta, Entonces no se puede reprogramar y cancelar sería tardío', () => {
    expect(puedeReprogramar(cita(limite(-1)), AHORA)).toBe(false)
    expect(cancelacionSeraTardia(cita(limite(-1)), AHORA)).toBe(true)
  })

  it('Dado el instante exacto del límite, Cuando se consulta, Entonces ya no se puede (el límite es estricto)', () => {
    expect(puedeReprogramar(cita(limite(0)), AHORA)).toBe(false)
  })

  it('Dado que el backend no mandó el límite, Cuando se consulta, Entonces se deja intentar y no se anuncia tardía', () => {
    expect(puedeReprogramar(cita(undefined), AHORA)).toBe(true)
    expect(cancelacionSeraTardia(cita(undefined), AHORA)).toBe(false)
  })

  it('Dadas las horas de antelación, Cuando se escriben, Entonces concuerda el singular y el plural', () => {
    expect(textoHoras(1)).toBe('1 hora')
    expect(textoHoras(2)).toBe('2 horas')
    expect(textoHoras(undefined)).toBe('la antelación mínima')
  })
})
