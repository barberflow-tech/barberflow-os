import { describe, expect, it } from 'vitest'
import {
  atiendeEl,
  diaSemana,
  primerDiaLaboral,
  proximosDiasLaborales,
  sumarDias,
} from './diasLaborales'

// 2026-11-16 es lunes (0); 2026-11-22 es domingo (6).
const LUNES = '2026-11-16'
const DOMINGO = '2026-11-22'
const LUN_A_SAB = [0, 1, 2, 3, 4, 5]

describe('diasLaborales', () => {
  it('Dada una fecha, Cuando se pide su día, Entonces usa 0 lunes … 6 domingo como el backend', () => {
    expect(diaSemana(LUNES)).toBe(0)
    expect(diaSemana('2026-11-20')).toBe(4)
    expect(diaSemana(DOMINGO)).toBe(6)
  })

  it('Dado un horario de lunes a sábado, Cuando se consulta un domingo, Entonces no atiende', () => {
    expect(atiendeEl(LUN_A_SAB, LUNES)).toBe(true)
    expect(atiendeEl(LUN_A_SAB, DOMINGO)).toBe(false)
  })

  it('Dado que no hay dato del horario, Cuando se consulta, Entonces se asume que atiende', () => {
    expect(atiendeEl(undefined, DOMINGO)).toBe(true)
  })

  it('Dado un barbero sin ningún día configurado, Cuando se consulta, Entonces nunca atiende', () => {
    expect(atiendeEl([], LUNES)).toBe(false)
  })

  it('Dado un cambio de mes o de año, Cuando se suman días, Entonces la fecha sigue siendo válida', () => {
    expect(sumarDias('2026-11-30', 1)).toBe('2026-12-01')
    expect(sumarDias('2026-12-31', 1)).toBe('2027-01-01')
  })

  it('Dado un horario de lunes a sábado, Cuando se piden los próximos días, Entonces se salta el domingo', () => {
    // sáb 21, (dom 22 fuera), lun 23, mar 24, mié 25
    expect(proximosDiasLaborales('2026-11-21', LUN_A_SAB, 4)).toEqual([
      '2026-11-21',
      '2026-11-23',
      '2026-11-24',
      '2026-11-25',
    ])
  })

  it('Dado que hoy no se atiende, Cuando se pide el primer día, Entonces es el siguiente laborable', () => {
    expect(primerDiaLaboral(DOMINGO, LUN_A_SAB)).toBe('2026-11-23')
    expect(primerDiaLaboral(LUNES, LUN_A_SAB)).toBe(LUNES)
  })

  it('Dado un barbero sin horario, Cuando se piden días laborables, Entonces no hay ninguno y no se cicla', () => {
    expect(proximosDiasLaborales(LUNES, [], 7)).toEqual([])
    expect(primerDiaLaboral(LUNES, [])).toBeNull()
  })
})
