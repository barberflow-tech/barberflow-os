import { describe, expect, it } from 'vitest'
import { clienteSchema } from './reservaSchema'

describe('clienteSchema', () => {
  it('acepta nombre completo y celular colombiano de 10 dígitos', () => {
    // Dado un nombre completo y un celular válido
    // Cuando se valida el formulario del paso 4
    const resultado = clienteSchema.safeParse({
      nombre: 'Juan Esteban Gómez',
      celular: '300 456 7890',
    })

    // Entonces los datos son válidos y el celular queda sin espacios
    expect(resultado.success).toBe(true)
    if (resultado.success) expect(resultado.data.celular).toBe('3004567890')
  })

  it('rechaza un nombre vacío o demasiado corto', () => {
    const resultado = clienteSchema.safeParse({ nombre: 'Jo', celular: '3004567890' })

    expect(resultado.success).toBe(false)
    if (!resultado.success) {
      expect(resultado.error.issues[0].path).toEqual(['nombre'])
    }
  })

  it.each(['12345', '2004567890', '30045678901', 'abcdefghij'])(
    'rechaza el celular inválido %s',
    (celular) => {
      const resultado = clienteSchema.safeParse({ nombre: 'Juan Gómez', celular })

      expect(resultado.success).toBe(false)
      if (!resultado.success) {
        expect(resultado.error.issues[0].path).toEqual(['celular'])
      }
    },
  )
})
