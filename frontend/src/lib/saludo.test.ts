import { describe, expect, it } from 'vitest'
import { primerNombre, saludoSegunHora } from './saludo'

describe('saludoSegunHora', () => {
  it.each([5, 8, 11])(
    'Dado las %i h, Cuando se saluda, Entonces dice «Buenos días»',
    (h) => {
      expect(saludoSegunHora(h)).toBe('Buenos días')
    },
  )

  it.each([12, 15, 18])(
    'Dado las %i h, Cuando se saluda, Entonces dice «Buenas tardes»',
    (h) => {
      expect(saludoSegunHora(h)).toBe('Buenas tardes')
    },
  )

  it.each([19, 23, 0, 4])(
    'Dado las %i h, Cuando se saluda, Entonces dice «Buenas noches»',
    (h) => {
      expect(saludoSegunHora(h)).toBe('Buenas noches')
    },
  )
})

describe('primerNombre', () => {
  it('Dado un nombre completo, Cuando se pide el primer nombre, Entonces devuelve solo la primera palabra', () => {
    expect(primerNombre('Ana Pérez')).toBe('Ana')
    expect(primerNombre('  Luis   Fernando Gómez ')).toBe('Luis')
  })

  it('Dado un nombre vacío o ausente, Cuando se pide el primer nombre, Entonces devuelve texto vacío', () => {
    expect(primerNombre('')).toBe('')
    expect(primerNombre('   ')).toBe('')
    expect(primerNombre(undefined)).toBe('')
  })
})
