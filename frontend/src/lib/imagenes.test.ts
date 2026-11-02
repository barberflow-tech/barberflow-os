import { describe, expect, it } from 'vitest'
import { MAX_BYTES, validarImagen } from './imagenes'

function archivo(nombre: string, tipo: string, bytes = 1024) {
  const f = new File(['x'], nombre, { type: tipo })
  Object.defineProperty(f, 'size', { value: bytes })
  return f
}

describe('validarImagen', () => {
  it.each([
    ['foto.png', 'image/png'],
    ['foto.jpg', 'image/jpeg'],
    ['foto.webp', 'image/webp'],
  ])('acepta %s', (nombre, tipo) => {
    expect(validarImagen(archivo(nombre, tipo))).toBeNull()
  })

  it('acepta un archivo de exactamente 5 MB', () => {
    expect(validarImagen(archivo('foto.png', 'image/png', MAX_BYTES))).toBeNull()
  })

  it('rechaza un archivo que supera 5 MB', () => {
    expect(validarImagen(archivo('foto.png', 'image/png', MAX_BYTES + 1))).toMatch(
      /5 MB/,
    )
  })

  it.each([
    ['doc.pdf', 'application/pdf'],
    ['animada.gif', 'image/gif'],
    ['vector.svg', 'image/svg+xml'],
    ['sin-tipo', ''],
  ])('rechaza %s por formato', (nombre, tipo) => {
    expect(validarImagen(archivo(nombre, tipo))).toMatch(/PNG, JPG o WEBP/)
  })
})
