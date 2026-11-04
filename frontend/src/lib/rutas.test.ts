import { describe, expect, it } from 'vitest'
import { rutaPorRol } from './rutas'

describe('rutaPorRol', () => {
  it('envía a cada rol a su pantalla inicial', () => {
    expect(rutaPorRol('admin')).toBe('/admin')
    expect(rutaPorRol('cliente')).toBe('/reservar')
    expect(rutaPorRol('barbero')).toBe('/barbero/portafolio')
  })
})
